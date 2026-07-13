import base64
import io
import os
import re
from collections import defaultdict

from dotenv import load_dotenv
from PIL import Image, ImageEnhance, ImageOps
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from services.schemas import ReceiptAnalysisSchema, ReceiptListAnalysisSchema

load_dotenv()

POSTGRES_ASYNC_URL = os.getenv("DATABASE_URL_DOCKER")


def get_isolated_session() -> AsyncSession:

    assert POSTGRES_ASYNC_URL is not None, "DATABASE_URL environment variable is not set"
    engine = create_async_engine(POSTGRES_ASYNC_URL, echo=False, poolclass=NullPool)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    return session_maker()


def merge_ocr_blocks_to_text(rapid_results, y_threshold: int = 12) -> str:
    if not rapid_results:
        return ""

    lines_dict: defaultdict[float, list[tuple[float, str]]] = defaultdict(list)

    for line in rapid_results:
        cords = line[0]
        text = line[1]

        # 🔥 ДОБАВЛЕНО: Удаляем китайские/японские/корейские иероглифы (весь блок CJK)
        # Они больше всего ломают мозг модели gpt-4o-mini
        text = re.sub(r"[\u4e00-\u9fff]+", "", text)
        # Убираем лишние двойные пробелы, которые могли остаться после удаления
        text = " ".join(text.split())

        y_center = sum(point[1] for point in cords) / 4
        x_center = sum(point[0] for point in cords) / 4

        matched_y = None
        for existing_y in lines_dict.keys():
            if abs(existing_y - y_center) <= y_threshold:
                matched_y = existing_y
                break

        if matched_y is not None:
            lines_dict[matched_y].append((x_center, text))
        else:
            lines_dict[y_center].append((x_center, text))

    final_lines = []
    for y in sorted(lines_dict.keys()):
        sorted_words = sorted(lines_dict[y], key=lambda item: item[0])
        # Игнорируем пустые строки, если там были только иероглифы
        line_text = " ".join(word[1] for word in sorted_words if word[1].strip())
        if line_text:
            final_lines.append(line_text)

    return "\n".join(final_lines)


#
# import re
# from collections import defaultdict


# import re
#
#
# def merge_ocr_blocks_to_text(rapid_results, y_threshold: int = 6) -> str:
#     # 1. Защита от пустого ввода
#     if not rapid_results:
#         return ""
#
#     flat_elements = []
#
#     for line in rapid_results:
#         # Защита от некорректной структуры элемента
#         if not line or len(line) < 2:
#             continue
#
#         cords = line[0]
#         raw_text = line[1]
#
#         # RapidOCR может вернуть кортеж (text, conf) или просто строку text.
#         # Приводим к строке в любом случае:
#         if isinstance(raw_text, (list, tuple)) and len(raw_text) > 0:
#             text = str(raw_text[0])
#         else:
#             text = str(raw_text)
#
#         # Удаляем CJK иероглифы (китайский/японский/корейский шум)
#         text = re.sub(r'[\u4e00-\u9fff]+', '', text)
#         text = " ".join(text.split())
#
#         # Если после очистки строка пустая — пропускаем
#         if not text.strip():
#             continue
#
#         # Защита: проверяем, что у нас есть 4 точки координат
#         if not cords or len(cords) < 4:
#             continue
#
#         try:
#             # Считаем центры масс
#             y_center = sum(point[1] for point in cords) / 4
#             x_center = sum(point[0] for point in cords) / 4
#             flat_elements.append({"x": x_center, "y": y_center, "text": text})
#         except (IndexError, TypeError):
#             continue  # Пропускаем, если структура точек сломалась
#
#     # 2. ВАЖНАЯ ЗАЩИТА: Если после фильтрации не осталось элементов, возвращаем пустую строку
#     if not flat_elements:
#         return ""
#
#     # Сортируем абсолютно все элементы по вертикали (Y)
#     flat_elements.sort(key=lambda item: item["y"])
#
#     lines = []
#     current_line = [flat_elements[0]]  # Теперь тут никогда не упадет
#
#     # 3. Группируем в строки на основе соседа
#     for element in flat_elements[1:]:
#         if abs(element["y"] - current_line[-1]["y"]) <= y_threshold:
#             current_line.append(element)
#         else:
#             lines.append(current_line)
#             current_line = [element]
#
#     if current_line:
#         lines.append(current_line)
#
#     # 4. Собираем финальный текст, сортируя элементы внутри строк по горизонтали (X)
#     final_lines = []
#     for line in lines:
#         line.sort(key=lambda item: item["x"])
#         line_text = " ".join(item["text"] for item in line)
#         final_lines.append(line_text)
#
#     return "\n".join(final_lines)


def process_receipt_to_base64(file_io: io.BytesIO) -> str:

    img: Image.Image
    with Image.open(file_io) as img:
        # 1. Конвертируем в RGB (если вдруг пришел PNG в RGBA, убираем альфа-канал)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        else:
            img = img.convert("RGB")

        # 2. Умный РЕСАЙЗ (Уменьшаем вес, сохраняя читаемость мелкого шрифта)
        # Для OpenAI идеальный размер по длинной стороне — около 1500-2000px
        max_size = 1800
        original_width, original_height = img.size

        if max(original_width, original_height) > max_size:
            if original_width > original_height:
                new_width = max_size
                new_height = int(original_height * (max_size / original_width))
            else:
                new_height = max_size
                new_width = int(original_width * (max_size / original_height))
            # Используем высококачественный фильтр ресайза Resampling.LANCZOS
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # 3. МЯГКОЕ улучшение контраста (не выжигаем белое)
        # 1.2 - 1.3 вполне достаточно, чтобы сделать буквы отчетливее
        contrast = ImageEnhance.Contrast(img)
        img = contrast.enhance(1.25)

        # 4. МЯГКОЕ улучшение резкости (убираем размытие камеры, но не создаем шум)
        sharpness = ImageEnhance.Sharpness(img)
        img = sharpness.enhance(1.3)

        # 5. Мягкий автоконтраст без фанатизма
        img = ImageOps.autocontrast(img, cutoff=1)

        # 6. Сохраняем в JPEG с хорошим качеством
        output_buffer = io.BytesIO()
        img.save(
            output_buffer, format="JPEG", quality=85
        )  # 85 - стандарт золотого сечения вес/качество
        processed_bytes = output_buffer.getvalue()

    base64_image = base64.b64encode(processed_bytes).decode("utf-8")
    return f"data:image/jpeg;base64,{base64_image}"


LEET_MAP = {
    "b": "б",
    "M": "м",
    "a": "а",
    "r": "р",
    "P": "р",
    "W": "и",
    "6": "б",
    "5": "б",
    "x": "х",
    "e": "е",
    "H": "н",
    "O": "о",
    "B": "в",
    "4": "ч",
    "E": "е",
    "K": "к",
    "c": "с",
    "k": "к",
    "y": "у",
    "n": "н",
    "p": "п",
    "u": "и",
    "3": "з",
    "S": "с",
    "T": "т",
}


def decode_visual_translit(text: str) -> str:
    if not text:
        return ""

    # Шаг 1. Безопасная замена букв (буквы на буквы не ломают цены!)
    # Этот шаг можно делать глобально по всему тексту
    letter_map = str.maketrans(
        {
            "A": "А",
            "a": "а",
            "B": "В",
            "C": "С",
            "c": "с",
            "E": "Е",
            "e": "е",
            "H": "Н",
            "K": "К",
            "k": "к",
            "M": "М",
            "O": "О",
            "o": "о",
            "P": "Р",
            "p": "р",
            "T": "Т",
            "t": "т",
            "X": "Х",
            "x": "х",
            "y": "у",
            "r": "г",
            "u": "и",
            "n": "н",
            "b": "б",
        }
    )
    decoded = text.translate(letter_map)

    # Шаг 2. Контекстная замена ЦИФР на БУКВЫ (Магия регулярных выражений)
    # Мы заменяем цифры только если они граничат с буквами (латинскими или русскими)

    # 4 -> ч (если рядом буквы, например, 'KACCOBb4EK' -> 'КАССОВЫЧЕК')
    decoded = re.sub(r"(?<=[a-zA-Zа-яА-Я])4|4(?=[a-zA-Zа-яА-Я])", "ч", decoded)

    # 3 -> з (например, '0326309T.eneHuS' -> 'Т.еленеш')
    decoded = re.sub(r"(?<=[a-zA-Zа-яА-Я])3|3(?=[a-zA-Zа-яА-Я])", "з", decoded)

    # 5 -> б (например, 'CaM5ePW' -> 'Самбери')
    decoded = re.sub(r"(?<=[a-zA-Zа-яА-Я])5|5(?=[a-zA-Zа-яА-Я])", "б", decoded)

    # 6 -> б или ь (в зависимости от контекста, чаще 'б' в именах собственных)
    decoded = re.sub(r"(?<=[a-zA-Zа-яА-Я])6|6(?=[a-zA-Zа-яА-Я])", "б", decoded)

    # 8 -> я (очень частая ошибка OCR в конце слов, например, 'MoHaCTbIPCka8' -> 'Монастырская')
    decoded = re.sub(r"(?<=[a-zA-Zа-яА-Я])8|8(?=[a-zA-Zа-яА-Я])", "я", decoded)

    # Шаг 3. Точечные исправления известных брендов и шума
    replacements = {
        r"\b000\b": "ООО",  # Заменяем '000' на 'ООО' только если это отдельное слово
        r"lokynaTenb": "покупатель",
        r"CaMбePW": "Самбери",  # с учетом того, что 5 уже заменилось на б
        r"CaMбePи": "Самбери",
        r"byMara": "бумага",
        r"TyaneTHaA": "туалетная",
        r"MopOxeHOe": "мороженое",
        r"WoKonaA": "шоколад",
        r"yBenka": "Увелка",
        r"nakeT-Mauka": "пакет-майка",
        r"Hera3MPOBaHH": "негазированная",
        r"Hera3MP0BaHH": "негазированная",
        r"BoAз": "вода",
        r"Bona": "вода",
        r"BoAa": "вода",
        r"CanaT npM6On": "салат прибой",
    }

    for pattern, repl in replacements.items():
        decoded = re.sub(pattern, repl, decoded, flags=re.IGNORECASE)

    return decoded


# def merge_transactions_by_category(analysis_result: ReceiptListAnalysisSchema) -> ReceiptListAnalysisSchema:
#     """
#     Группирует транзакции одной категории внутри одного ответа ИИ.
#     Суммирует их amount и объединяет списки items.
#     """
#     grouped_transactions = {}
#
#     for trans in analysis_result.transactions:
#         if trans.category in grouped_transactions:
#             grouped_transactions[trans.category].amount += trans.amount
#             grouped_transactions[trans.category].items.extend(trans.items)
#         else:
#
#             grouped_transactions[trans.category] = trans
#
#
#     analysis_result.transactions = list(grouped_transactions.values())
#     return analysis_result


def merge_transactions_by_category(
    analysis_result: ReceiptListAnalysisSchema,
) -> ReceiptListAnalysisSchema:

    #merged_map = {}
    merged_map: dict[tuple[str, str], ReceiptAnalysisSchema] = {}

    for tx in analysis_result.transactions:
        key = (tx.type, tx.category)

        if key not in merged_map:

            merged_map[key] = ReceiptAnalysisSchema(
                type=tx.type,
                category=tx.category,
                amount=tx.amount,
                description=tx.description,
                items=list(tx.items),
            )
        else:

            merged_map[key].amount += tx.amount
            merged_map[key].items.extend(tx.items)

            if tx.description and tx.description != merged_map[key].description:
                current_desc = merged_map[key].description
                if current_desc:
                    merged_map[key].description = f"{current_desc}, {tx.description}"
                else:
                    merged_map[key].description = tx.description


    new_result = analysis_result.model_copy(deep=True)
    new_result.transactions = list(merged_map.values())
    return new_result
