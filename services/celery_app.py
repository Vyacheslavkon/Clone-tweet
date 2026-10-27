import os

from celery import Celery
from celery.signals import after_setup_logger, worker_shutdown
from dotenv import load_dotenv
from loguru import logger as log

from core.db_worker import close_worker_db_engine
from financial_bot.highload_bot import close_shared_bot
from logger_config import setup_logging
from services.analysis_cache import close_worker_cache
from services.worker_loop import close_worker_loop, get_worker_loop

load_dotenv()

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

app = Celery(
    "financial_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["financial_bot.tasks.ai", "financial_bot.tasks.vehicle_reports"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@after_setup_logger.connect
def setup_celery_logger(logger, *args, **kwargs) -> None:
    setup_logging()


@worker_shutdown.connect
def on_worker_shutdown(**kwargs) -> None:
    loop = get_worker_loop()

    for name, cleanup_coro_factory in [
        ("Redis cache", close_worker_cache),
        ("DB engine", close_worker_db_engine),
        ("Shared bot session", close_shared_bot),
    ]:
        try:
            loop.run_until_complete(cleanup_coro_factory())
        except Exception as e:  # noqa: PIE786 - shutdown cleanup fallback

            log.opt(exception=e).error(
                "Failed to close {name} during shutdown", name=name
            )

    close_worker_loop()
