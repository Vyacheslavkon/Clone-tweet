import os
import base64
import io

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


def process_receipt_to_base64(file_io: io.BytesIO) -> str:

    with Image.open(file_io) as img:

        img = ImageOps.grayscale(img)

        contrast = ImageEnhance.Contrast(img)
        img = contrast.enhance(2.5)

        sharpness = ImageEnhance.Sharpness(img)
        img = sharpness.enhance(2.0)

        img = ImageOps.autocontrast(img, cutoff=2)

        output_buffer = io.BytesIO()
        img.save(output_buffer, format="JPEG", quality=90)
        processed_bytes = output_buffer.getvalue()

    base64_image = base64.b64encode(processed_bytes).decode('utf-8')
    return f"data:image/jpeg;base64,{base64_image}"


async def async_process_receipt(chat_id: int, db_user_id: int, file_id: str):

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

        msg_text = (
            f"✅ <b>The check has been processed successfully!</b>\n\n"
            f"🏬 Description: {analysis_result.description or 'Неизвестно'}\n"
            f"💰 Amount: {analysis_result.amount} {analysis_result.currency}\n"
            f"🗂 Category: {analysis_result.category}\n\n"
            f"🧾 Positions have been added to your detailed statistics."
        )
        await bot.send_message(chat_id=chat_id, text=msg_text)

    except Exception as e:
        logger.error(f"Error processing check for user {db_user_id}: {e}", exc_info=True)

        await session.rollback()

        await bot.send_message(
            chat_id=chat_id,
            text="❌ Unfortunately, we couldn't recognize your receipt. Please make sure the photo is clear and try again."
        )

    finally:
        await session.close()
        await bot_session.close()


# if any(item.category == "other" and "батон" in item.name.lower() for item in analysis_result.items):
#     raise ValueError("Подозрение на ошибку OCR")
#
# except Exception:
# # 2. Если мини-модель ошиблась или сработал наш триггер — включаем тяжелую артиллерию
# logger.warning(f"gpt-4o-mini не справился. Переключаемся на gpt-4o для юзера {db_user_id}")
#
# model_to_use = "gpt-4o"
# analysis_result = await ai_service.analyze_image(
#     model=model_to_use,
#     image_url=image_data_url,
#     response_schema=ReceiptAnalysisSchema,
#     system_prompt=RECEIPT_SYSTEM_PROMPT
# )