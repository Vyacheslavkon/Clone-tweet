import base64
import io
import os
import re
from collections import defaultdict, Counter
from typing import Dict, Callable, List
from loguru import logger

from dotenv import load_dotenv
from PIL import Image, ImageEnhance, ImageOps
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from services.schemas import ReceiptAnalysisSchema, ReceiptListAnalysisSchema
from typing import List, Dict, Tuple
from services.schemas import ReceiptListAnalysisSchema

load_dotenv()

POSTGRES_ASYNC_URL = os.getenv("DATABASE_URL_DOCKER")


def get_isolated_session() -> AsyncSession:

    assert (
        POSTGRES_ASYNC_URL is not None
    ), "DATABASE_URL environment variable is not set"
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

    # merged_map = {}
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

CATEGORY_TITLES: Dict[str, str] = {
        "food": "🍎 Еда",
        "home": "🏠 Дом/Аренда",
        "entertainment": "🎉 Развлечения",
        "transport": "🚗 Транспорт",
        "health": "💊 Здоровье",
        "other": "📦 Другое"
    }



def render_category_tree(
        cat_key: str,
        data: dict,
        _: Callable[[str], str],
        max_visible_items: int = 5
) -> List[str]:

    tree_lines = []

    system_keys_transactions = {
        "food": _("Food"),
        "health": _("Health"),
        "transport": _("Transport"),
        "entertainment": _("Entertainment"),
        "home": _("Home"),
        "other": _("Other")
    }

    category_items = []
    for item in data.get("top_items", []):
        if item["category"] == cat_key:
            name_raw = item["name"].strip()
            name_lower = name_raw.lower()

            if name_lower in system_keys_transactions:

                category_items.append(system_keys_transactions[name_lower])

            elif "system_category_" in name_lower:
                clean_key = name_lower.replace("system_category_", "")
                category_items.append(system_keys_transactions.get(clean_key, clean_key))

            else:

                category_items.append(name_raw)

    if not category_items:
        return tree_lines

    item_counts = Counter(category_items)
    all_unique_items = item_counts.most_common()

    visible_items = all_unique_items[:max_visible_items]
    for item_name, item_freq in visible_items:
        tree_lines.append(f"     └ {item_name} — {item_freq}")

    total_items_count = len(category_items)
    visible_items_count = sum(freq for _, freq in visible_items)
    hidden_items_count = total_items_count - visible_items_count

    if hidden_items_count > 0:
        tree_lines.append(_("     └ Other operations — {count}").format(count=hidden_items_count))

    return tree_lines


def render_monthly_tree(data: dict, _: Callable[[str], str]) -> List[str]:
    category_titles = {
        "food": _("Groceries and food"),
        "health": _("Health and Medicine"),
        "transport": _("Transport and Automotive"),
        "entertainment": _("Entertainment and leisure"),
        "home": _("Home and Household"),
        "other": _("Other expenses")
    }

    essential_categories = ["food", "health", "home"]
    discretionary_categories = ["transport", "entertainment", "other"]

    tree_lines = [_("\n🟢 <u>Necessary :</u>")]

    for cat_data in data.get("categories", []):
        cat_key = cat_data["category"]

        if cat_key in essential_categories:
            tree_lines.append(_(" • <b>{cat_name}</b> — <b>{count} transactions per month</b>").format(
                cat_name=category_titles.get(cat_key, cat_key).upper(),
                count=cat_data["count"]
            ))
            tree_lines.extend(render_category_tree(cat_key, data, _))

    tree_lines.append(_("\n🟡 <u>Secondary :</u>"))

    for cat_data in data.get("categories", []):
        cat_key = cat_data["category"]
        if cat_key in discretionary_categories:
            tree_lines.append(_(" • <b>{cat_name}</b> — <b>{count} transactions per month</b>").format(
                cat_name=category_titles.get(cat_key, cat_key).upper(),
                count=cat_data["count"]
            ))

            tree_lines.extend(render_category_tree(cat_key, data, _))

    return tree_lines


def format_weekly_block(
        items_list: list,
        _: Callable[[str], str],
        max_items: int
) -> List[str]:

    block_lines = []
    if not items_list:
        block_lines.append(_("   • No expenses for the period"))
        return block_lines

    counts = Counter(items_list)

    for name, freq in counts.most_common(max_items):
        block_lines.append(f"   • <b>{name}</b> — {freq} " + _("transaction(s)"))

    return block_lines


def render_weekly_top(
        data: dict,
        _: Callable[[str], str],
        max_items: int = 10
) -> List[str]:

    tree_lines = []


    essential_categories = {"food", "health", "home"}

    system_keys_transactions = {
        "food": _("Food"),
        "health": _("Health"),
        "transport": _("Transport"),
        "entertainment": _("Entertainment"),
        "home": _("Home"),
        "other": _("Other")
    }

    essential_items = []
    discretionary_items = []

    for item in data.get("top_items", []):
        cat_key = item.get("category", "other")
        name_raw = item["name"].strip()
        name_lower = name_raw.lower()


        if name_lower in system_keys_transactions:
            display_name = system_keys_transactions[name_lower]
        elif "system_category_" in name_lower:
            clean_key = name_lower.replace("system_category_", "")
            display_name = system_keys_transactions.get(clean_key, clean_key)
        else:
            display_name = name_raw


        if cat_key in essential_categories:
            essential_items.append(display_name)
        else:
            discretionary_items.append(display_name)


    tree_lines.append(_("\n🟢 <u>Necessary :</u>"))
    tree_lines.extend(format_weekly_block(essential_items, _, max_items))

    tree_lines.append(_("\n🟡 <u>Secondary :</u>"))
    tree_lines.extend(format_weekly_block(discretionary_items, _, max_items))

    return tree_lines


def render_detailed_transactions(data: dict, _: Callable[[str], str]) -> str:

    category_titles = {
        "food": _("Food"),
        "health": _("Health"),
        "transport": _("Transport"),
        "entertainment": _("Entertainment"),
        "home": _("Home"),
        "other": _("Other")
    }

    report_lines = [
        _("🧾 <b>Detailed Transaction History</b>\n"),
    ]


    raw_items = data.get("top_items", [])
    try:
        sorted_items = sorted(raw_items, key=lambda x: x.get("date", ""), reverse=True)
    except TypeError as type_err:

        logger.warning(
            "Failed to sort transactions by date due to mismatched types. "
            "Using fallback unsorted data. Error: %s", type_err
        )

        sorted_items = raw_items

    current_group_date = None
    currency = data.get("user_config", {}).get("currency", "RUB")

    for item in sorted_items:
        item_date = item.get("date", "")

        if item_date != current_group_date:
            current_group_date = item_date
            report_lines.append(f"\n📅 <b>{item_date}</b>")

        cat_key = item.get("category", "other")
        cat_title = category_titles.get(cat_key, cat_key)
        name_raw = item.get("name", "").strip()
        name_lower = name_raw.lower()


        if name_lower in category_titles or "system_category" in name_lower or "operation" in name_lower:

            display_name = f"✍️ {cat_title}"
        else:

            display_name = f"🛒 {name_raw} ({cat_title})"

        amount = item.get("total_amount", 0.0)

        report_lines.append(f"  • {display_name} — <b>{round(amount, 2)} {currency}</b>")

    if not sorted_items:
        report_lines.append(_("No transactions found for this period."))

    return "\n".join(report_lines)



def render_receipt_report(
        analysis_result: ReceiptListAnalysisSchema,
        _
) -> Tuple[str, str]:

    income_txs = [t for t in analysis_result.transactions if t.type == "income"]
    expense_txs = [t for t in analysis_result.transactions if t.type == "expense"]

    total_income = sum(t.amount for t in income_txs)
    total_expense = sum(t.amount for t in expense_txs)

    icons = {
        "food": "🍏",
        "transport": "🚗",
        "home": "🏠",
        "entertainment": "🎉",
        "health": "💊",
        "other": "📦",
        "salary": "💼",
        "bonus": "📈",
        "gift": "🎁",
        "deal": "🤝"
    }

    report_chunks = [_("✅ <b>Operations successfully recorded!</b>\n")]


    if income_txs:
        report_chunks.append(_("💰 <b>Received Income:</b>"))
        income_details = []
        for tx in income_txs:
            icon = icons.get(tx.category, "💵")
            localized_category = _(tx.description.capitalize() if tx.description else "Other")
            items_lines = [f"  • {item.name}: <b>{item.price}</b>" for item in tx.items]
            items_str = "\n" + "\n".join(items_lines) if items_lines else ""
            income_details.append(f"{icon} {localized_category}: <b>+{tx.amount}</b>{items_str}")
        report_chunks.append("\n".join(income_details))

    if income_txs and expense_txs:
        report_chunks.append(" ")


    if expense_txs:
        report_chunks.append(_("📉 <b>Spent Expenses:</b>"))
        expense_details = []
        for tx in expense_txs:
            icon = icons.get(tx.category, "📦")
            localized_category = _(tx.category.capitalize())
            items_lines = [
                f"  • {item.name}: <b>{item.price}</b>" if item.price > 0 else f"  • {item.name}"
                for item in tx.items
            ]
            items_str = "\n".join(items_lines)
            expense_details.append(_("{icon} {category}: <b>-{amount}</b>\n{items}").format(
                icon=icon, category=localized_category, amount=tx.amount, items=items_str
            ))
        report_chunks.append("\n".join(expense_details))


    report_chunks.append("\n" + "─" * 20)
    meta_lines = []
    if total_income > 0:
        meta_lines.append(_("Total Income: <b>+{total_amount}</b>").format(total_amount=total_income))
    if total_expense > 0:
        meta_lines.append(_("Total Expenses: <b>-{total_amount}</b>").format(total_amount=total_expense))
    report_chunks.append("\n".join(meta_lines))

    msg_text = "\n".join(report_chunks)


    if income_txs and not expense_txs:
        localized_button_label = _("❌ cancel income")
    elif expense_txs and not income_txs:
        localized_button_label = _("❌ cancel expense")
    else:
        localized_button_label = _("❌ cancel operation")

    return msg_text, localized_button_label
