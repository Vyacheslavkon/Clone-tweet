import os

from celery import Celery
from celery.signals import after_setup_logger
from dotenv import load_dotenv
import asyncio
from celery.signals import worker_shutdown
from logger_config import setup_logging

from financial_bot.highload_bot import close_shared_bot

load_dotenv()

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

app = Celery(
    "financial_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["financial_bot.tasks.ai"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@after_setup_logger.connect
def setup_celery_logger(logger, *args, **kwargs):
    setup_logging()


@worker_shutdown.connect
def on_worker_shutdown(sender, **kwargs):

    print("Celery worker is shutting down. Cleaning up global resources...")

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        asyncio.ensure_future(close_shared_bot())

    else:
        loop.run_until_complete(close_shared_bot())