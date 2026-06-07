import asyncio

from dotenv import load_dotenv

from services.celery_app import app
from services.pipelines import async_process_receipt

load_dotenv()

celery_app = app



@celery_app.task(name="financial_bot.ai.process_receipt_task", rate_limit="2/s")
def process_receipt_task(chat_id: int, db_user_id: int, file_id: str):

    asyncio.run(async_process_receipt(chat_id, db_user_id, file_id))
