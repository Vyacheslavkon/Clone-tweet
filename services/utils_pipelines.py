import os
import base64
import io
import re
from collections import defaultdict

from loguru import logger
from PIL import Image, ImageEnhance, ImageOps
from dotenv import load_dotenv
from collections import defaultdict


from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

load_dotenv()

POSTGRES_ASYNC_URL = os.getenv("DATABASE_URL_DOCKER")


def get_isolated_session() -> AsyncSession:
    engine = create_async_engine(
        POSTGRES_ASYNC_URL,
        echo=False,
        poolclass=NullPool
    )

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    return session_maker()


# def merge_ocr_blocks_to_text(rapid_results, y_threshold: int = 15) -> str:
#     if not rapid_results:
#         return ""
#
#     lines_dict = defaultdict(list)
#
#     for line in rapid_results:
#         cords = line[0]
#         text = line[1]
#
#         # 🔥 ДОБАВЛЕНО: Удаляем китайские/японские/корейские иероглифы (весь блок CJK)
#         # Они больше всего ломают мозг модели gpt-4o-mini
#         text = re.sub(r'[\u4e00-\u9fff]+', '', text)
#         # Убираем лишние двойные пробелы, которые могли остаться после удаления
#         text = " ".join(text.split())
#
#         y_center = sum(point[1] for point in cords) / 4
#         x_center = sum(point[0] for point in cords) / 4
#
#         matched_y = None
#         for existing_y in lines_dict.keys():
#             if abs(existing_y - y_center) <= y_threshold:
#                 matched_y = existing_y
#                 break
#
#         if matched_y is not None:
#             lines_dict[matched_y].append((x_center, text))
#         else:
#             lines_dict[y_center].append((x_center, text))
#
#     final_lines = []
#     for y in sorted(lines_dict.keys()):
#         sorted_words = sorted(lines_dict[y], key=lambda item: item[0])
#         # Игнорируем пустые строки, если там были только иероглифы
#         line_text = " ".join(word[1] for word in sorted_words if word[1].strip())
#         if line_text:
#             final_lines.append(line_text)
#
#     return "\n".join(final_lines)

import re
from collections import defaultdict


def merge_ocr_blocks_to_text(rapid_results, y_threshold: int = 6) -> str:
    if not rapid_results:
        return ""

    flat_elements = []

    for line in rapid_results:
        cords = line[0]
        text = line[1]

        # Удаляем CJK иероглифы
        text = re.sub(r'[\u4e00-\u9fff]+', '', text)
        text = " ".join(text.split())

        # Если после очистки строка пустая — пропускаем
        if not text.strip():
            continue

        # Считаем центры масс
        y_center = sum(point[1] for point in cords) / 4
        x_center = sum(point[0] for point in cords) / 4

        flat_elements.append({"x": x_center, "y": y_center, "text": text})

    if not flat_elements:
        return ""

    # 1. Сортируем абсолютно все элементы по вертикали (Y)
    flat_elements.sort(key=lambda item: item["y"])

    lines = []
    current_line = [flat_elements[0]]

    # 2. Группируем в строки на основе соседа
    for element in flat_elements[1:]:
        # Сравниваем с последним добавленным элементом в текущей строке
        if abs(element["y"] - current_line[-1]["y"]) <= y_threshold:
            current_line.append(element)
        else:
            lines.append(current_line)
            current_line = [element]

    if current_line:
        lines.append(current_line)

    # 3. Собираем финальный текст, сортируя элементы внутри строк по горизонтали (X)
    final_lines = []
    for line in lines:
        line.sort(key=lambda item: item["x"])
        line_text = " ".join(item["text"] for item in line)
        final_lines.append(line_text)

    return "\n".join(final_lines)


def process_receipt_to_base64(file_io: io.BytesIO) -> str:
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
        img.save(output_buffer, format="JPEG", quality=85)  # 85 - стандарт золотого сечения вес/качество
        processed_bytes = output_buffer.getvalue()

    base64_image = base64.b64encode(processed_bytes).decode('utf-8')
    return f"data:image/jpeg;base64,{base64_image}"