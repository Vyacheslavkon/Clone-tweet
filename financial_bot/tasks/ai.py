import asyncio
import openai
from dotenv import load_dotenv
from loguru import logger

from services.celery_app import app
from services.pipelines import async_process_receipt

load_dotenv()

celery_app = app



@celery_app.task(name="financial_bot.ai.process_receipt_task", rate_limit="2/s")
def process_receipt_task(chat_id: int, db_user_id: int, locale: str, image_bytes: bytes):

    asyncio.run(async_process_receipt(chat_id, db_user_id, locale, image_bytes))


# @celery_app.task(name="financial_bot.ai.process_expense_task", rate_limit="2/s")
# def process_expense_task(chat_id: int, db_user_id: int, locale: str, voice_bytes: bytes):
#
#     asyncio.run(async_process_receipt(chat_id, db_user_id, locale, voice_bytes))


@celery_app.task(name="financial_bot.ai.process_expense_task",
                 bind=True,
                 max_retries=3)
def process_expense_task(self,chat_id: int, db_user_id: int, locale: str, voice_bytes: bytes):

    try:
        asyncio.run(async_process_receipt(chat_id, db_user_id, locale, voice_bytes))

    except openai.OpenAIError as exc:
        logger.warning(
            f"OpenAI API failure (request ID in the log above)."
            f"Retry attempt {self.request.retries + 1}/3. Error: {exc}"
        )
        # Рассчитываем экспоненциальную задержку: 2с, 4с, 8с...
        countdown = 2 ** self.request.retries

        # Передаем self.retry, он сам корректно перезапустит таску в Celery
        raise self.retry(exc=exc, countdown=countdown)

    except Exception as e:
        logger.error(f"Critical unhandled error in the task: {e}")
        raise e