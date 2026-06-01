import os

from dotenv import load_dotenv
from aiogram import Bot
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from loguru import logger

from services.client import ai_service
from services.schemas import ReceiptAnalysisSchema
from services.prompts import RECEIPT_SYSTEM_PROMPT
from financial_bot.repositories import save_receipt_to_db

load_dotenv()

POSTGRES_ASYNC_URL = os.getenv("DATABASE_URL_DOCKER")
BOT_TOKEN = os.getenv("BOT_TOKEN")


celery_engine = create_async_engine(POSTGRES_ASYNC_URL, echo=False)
celery_AsyncSessionLocal = async_sessionmaker(bind=celery_engine, expire_on_commit=False)


async def async_process_receipt(chat_id: int, db_user_id: int, file_id: str):

    bot = Bot(token=BOT_TOKEN)
    async with celery_AsyncSessionLocal() as session:
        try:
            # Получаем путь к файлу на серверах Telegram
            file_info = await bot.get_file(file_id)
            file_url = f"https://telegram.org{BOT_TOKEN}/{file_info.file_path}"

            analysis_result: ReceiptAnalysisSchema = await ai_service.analyze_image(
                image_url=file_url,
                response_schema=ReceiptAnalysisSchema,
                system_prompt=RECEIPT_SYSTEM_PROMPT
            )

            await save_receipt_to_db(
                session=session,
                user_id=db_user_id,
                analysis_result=analysis_result,
                photo_url=file_url,
                raw_text=str(analysis_result.model_dump())  # или любой кастомный текст
            )

            msg_text = (
                f"✅ **Чек успешно обработан!**\n\n"
                f"🏬 Магазин: {analysis_result.description or 'Неизвестно'}\n"
                f"💰 Сумма: {analysis_result.total_amount} {analysis_result.currency}\n"
                f"🗂 Категория: {analysis_result.category}\n\n"
                f"🧾 Позиции добавлены в вашу детальную статистику."
            )
            await bot.send_message(chat_id=chat_id, text=msg_text, parse_mode="Markdown")

        except Exception as e:
            # Здесь используем ваш loguru для логирования ошибок в Docker-контейнере

            logger.error(f"Ошибка при обработке чека для user {db_user_id}: {e}")

            await bot.send_message(
                chat_id=chat_id,
                text="❌ К сожалению, не удалось распознать чек. Пожалуйста, убедитесь, что фото четкое, и попробуйте снова."
            )
        finally:
            # Закрываем сессию бота
            await bot.session.close()