import os

from celery import Celery
from celery.signals import after_setup_logger
from dotenv import load_dotenv
import asyncio
from celery.signals import worker_shutdown
from logger_config import setup_logging
from loguru import logger as log
from financial_bot.highload_bot import close_shared_bot
from services.analysis_cache import close_worker_cache
from services.worker_loop import get_worker_loop, close_worker_loop
from core.db_worker import close_worker_db_engine

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


# @worker_shutdown.connect
# def on_worker_shutdown(**kwargs):
#     """Порядок важен: сначала закрываем то, что использует loop (Redis),
#     потом сам loop."""
#     loop = get_worker_loop()
#     try:
#         loop.run_until_complete(close_worker_cache())
#     finally:
#         close_worker_loop()


# new
@worker_shutdown.connect
def on_worker_shutdown(**kwargs):
    loop = get_worker_loop()

    for name, cleanup_coro_factory in [
        ("Redis cache", close_worker_cache),
        ("DB engine", close_worker_db_engine),
    ]:
        try:
            loop.run_until_complete(cleanup_coro_factory())
        except Exception as e:
            log.error("Failed to close %s during shutdown: %s", name, e, exc_info=True)

    close_worker_loop()