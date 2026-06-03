import os
import base64

from dotenv import load_dotenv
from aiogram import Bot
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from loguru import logger
from aiogram.utils.i18n import gettext as _

from services.client import ai_service
from services.schemas import ReceiptAnalysisSchema
from services.prompts import RECEIPT_SYSTEM_PROMPT
from financial_bot.repositories import save_receipt_to_db

load_dotenv()

POSTGRES_ASYNC_URL = os.getenv("DATABASE_URL_DOCKER")


celery_engine = create_async_engine(POSTGRES_ASYNC_URL, echo=False)
celery_AsyncSessionLocal = async_sessionmaker(bind=celery_engine, expire_on_commit=False)


async def async_process_receipt(chat_id: int, db_user_id: int, file_id: str, bot: Bot):

    async with celery_AsyncSessionLocal() as session:
        try:
            file_io = await bot.download(file_id)
            file_bytes = file_io.read()

            # 2. Кодируем байты в base64 для безопасной передачи в OpenAI/ProxyAPI
            base64_image = base64.b64encode(file_bytes).decode('utf-8')
            image_data_url = f"data:image/jpeg;base64,{base64_image}"

            # 3. Отправляем base64-строку вместо публичного URL бота
            analysis_result: ReceiptAnalysisSchema = await ai_service.analyze_image(
                image_url=image_data_url,  # Передаем Data URL с base64
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
