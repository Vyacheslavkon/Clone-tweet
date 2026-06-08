import os
import base64
import io
import gettext

from PIL import Image, ImageEnhance, ImageOps
from sqlalchemy.pool import NullPool
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from dotenv import load_dotenv
from aiogram import Bot
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from loguru import logger
from aiogram.utils.i18n import gettext as _
from pathlib import Path

from services.client import ai_service
from services.schemas import ReceiptAnalysisSchema
from services.prompts import RECEIPT_SYSTEM_PROMPT
from financial_bot.repositories import save_receipt_to_db

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


# def process_receipt_to_base64(file_io: io.BytesIO) -> str:
#
#     with Image.open(file_io) as img:
#
#         img = ImageOps.grayscale(img)
#
#         contrast = ImageEnhance.Contrast(img)
#         img = contrast.enhance(2.5)
#
#         sharpness = ImageEnhance.Sharpness(img)
#         img = sharpness.enhance(2.0)
#
#         img = ImageOps.autocontrast(img, cutoff=2)
#
#         output_buffer = io.BytesIO()
#         img.save(output_buffer, format="JPEG", quality=90)
#         processed_bytes = output_buffer.getvalue()
#
#     base64_image = base64.b64encode(processed_bytes).decode('utf-8')
#     return f"data:image/jpeg;base64,{base64_image}"


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
# async def async_process_receipt(chat_id: int, db_user_id: int, file_id: str):
#
#     bot_session = AiohttpSession()
#     bot = Bot(
#         token=os.getenv("BOT_TOKEN"),
#         session=bot_session,
#         default=DefaultBotProperties(parse_mode=ParseMode.HTML)
#     )
#
#     session = get_isolated_session()
#     try:
#         #file_io = await bot.download_file(file_path) (to improve productivity)
#         file_io = await bot.download(file_id)
#         image_data_url = process_receipt_to_base64(file_io)
#
#
#         analysis_result: ReceiptAnalysisSchema = await ai_service.analyze_image(
#             image_url=image_data_url,
#             response_schema=ReceiptAnalysisSchema,
#             system_prompt=RECEIPT_SYSTEM_PROMPT
#         )
#
#         await save_receipt_to_db(
#             session=session,
#             user_id=db_user_id,
#             analysis_result=analysis_result,
#             photo_url=None,
#             raw_text=analysis_result.model_dump_json()
#         )
#
#         msg_text = (
#             f"✅ <b>The check has been processed successfully!</b>\n\n"
#             f"🏬 Description: {analysis_result.description or 'Неизвестно'}\n"
#             f"💰 Amount: {analysis_result.amount} {analysis_result.currency}\n"
#             f"🗂 Category: {analysis_result.category}\n\n"
#             f"🧾 Positions have been added to your detailed statistics."
#         )
#         await bot.send_message(chat_id=chat_id, text=msg_text)
#
#     except Exception as e:
#         logger.error(f"Error processing check for user {db_user_id}: {e}", exc_info=True)
#
#         await session.rollback()
#
#         await bot.send_message(
#             chat_id=chat_id,
#             text="❌ Unfortunately, we couldn't recognize your receipt. Please make sure the photo is clear and try again."
#         )
#
#     finally:
#         await session.close()
#         await bot_session.close()



async def async_process_receipt(chat_id: int, db_user_id: int, file_id: str, locale: str):

    locales_dir = Path(__file__).resolve().parent.parent / "financial_bot" / "locales"

    try:
        lang = gettext.translation(
            domain='messages',
            localedir=str(locales_dir),  # gettext требует строку, а не объект Path
            languages=[locale],
            fallback=True
        )
    except Exception as e:
        logger.error(f"Не удалось загрузить локализацию из {locales_dir}: {e}")
        lang = gettext.NullTranslations()  # Фоллбек на оригинальный текст, если файлы не найдены

    _ = lang.gettext



    bot_session = AiohttpSession()
    bot = Bot(
        token=os.getenv("BOT_TOKEN"),
        session=bot_session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    session = get_isolated_session()
    try:
        #file_io = await bot.download_file(file_path) (to improve productivity)
        file_io = await bot.download(file_id)
        image_data_url = process_receipt_to_base64(file_io)


        analysis_result: ReceiptAnalysisSchema = await ai_service.analyze_image(
            image_url=image_data_url,
            response_schema=ReceiptAnalysisSchema,
            system_prompt=RECEIPT_SYSTEM_PROMPT
        )

        await save_receipt_to_db(
            session=session,
            user_id=db_user_id,
            analysis_result=analysis_result,
            photo_url=None,
            raw_text=analysis_result.model_dump_json()
        )

        msg_text = _((
            f"✅ <b>The check has been processed successfully!</b>\n\n"
            f"🏬 Description: {analysis_result.description or 'Неизвестно'}\n"
            f"💰 Amount: {analysis_result.amount} {analysis_result.currency}\n"
            f"🗂 Category: {analysis_result.category}\n\n"
            f"🧾 Positions have been added to your detailed statistics."
        ))
        await bot.send_message(chat_id=chat_id, text=msg_text)

    except Exception as e:
        logger.error(f"Error processing check for user {db_user_id}: {e}", exc_info=True)

        await session.rollback()

        await bot.send_message(
            chat_id=chat_id,
            text=_("❌ Unfortunately, we couldn't recognize your receipt. Please make sure the photo is clear and try again.")
        )

    finally:
        await session.close()
        await bot_session.close()