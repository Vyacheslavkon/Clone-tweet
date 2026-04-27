import os

from celery import Celery
from celery.signals import after_setup_logger

from logger_config import setup_logging

# Получаем URL брокера из переменных окружения (те, что в docker-compose)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

app = Celery(
    "financial_project",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    # Указываем Celery, где искать задачи (автоматическое сканирование)
    include=["financial_bot.tasks"],
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
