import asyncio
import os

from celery.signals import worker_process_init, worker_process_shutdown
from dotenv import load_dotenv
from loguru import logger
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from services.celery_app import app
from services.pipelines import async_process_receipt

load_dotenv()

celery_app = app

bot: Bot = None


@worker_process_init.connect
def init_bot_worker(**kwargs):

    global bot
    bot_token = os.getenv("BOT_TOKEN")


    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    logger.info(f"--- [Celery Worker] The bot has been successfully initialized for the process. ---")


@worker_process_shutdown.connect
def shutdown_bot_worker(**kwargs):

    global bot
    if bot:

        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(bot.session.close())
        else:
            loop.run_until_complete(bot.session.close())
        logger.info(f"--- [Celery Worker] The bot session was closed successfully ---")



@celery_app.task(name="financial_bot.ai.process_receipt_task")
def process_receipt_task(chat_id: int, db_user_id: int, file_id: str):
    asyncio.run(async_process_receipt(chat_id, db_user_id, file_id, bot))



