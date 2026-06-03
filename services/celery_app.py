import os
from dotenv import load_dotenv
from celery import Celery
from celery.signals import after_setup_logger

from logger_config import setup_logging

load_dotenv()

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

app = Celery(
    "financial_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["financial_bot.tasks.ai"],
)

# Дополнительные настройки ( сериализация и т.д.)
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
