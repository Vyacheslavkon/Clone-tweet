import os
from celery import Celery
from aiogram import Bot
from loguru import logger
from dotenv import load_dotenv

import asyncio

from services.celery_app import app

load_dotenv()

celery_app = app
bot = Bot(token=os.getenv("BOT_TOKEN"))


@celery_app.task(name="process_ai_request", queue="ai_tasks")
def process_ai_request(chat_id: int, message_id: int, user_prompt: str):
    try:
        logger.info("Starting AI processing for chat_id: {chat_id}", chat_id=chat_id)

        # 1. Запрос к AI (Пример с абстрактным API)
        # ai_response = call_your_ai_model(user_prompt)
        ai_response = f"The result of the analysis of your financial request: {user_prompt[:10]}... [Успешно]"

        # 2. Сохранение в PostgreSQL (через SQLAlchemy сессию, если нужно)
        # save_to_db(chat_id, ai_response)

        # 3. Отправка ответа в Telegram (редактируем «заглушку»)

        asyncio.run(bot.edit_message_text(
            text=ai_response,
            chat_id=chat_id,
            message_id=message_id
        ))

    except Exception as e:
        logger.error("Error in AI task: {e}", e=e)
        # Оповещаем пользователя об ошибке
        asyncio.run(bot.send_message(chat_id=chat_id, text="An error occurred while processing AI."))


# @celery_app.task
# def process_receipt_task(user_id: int, file_url: str):
#     # 1. Тяжелый запрос к AI (БД в это время отдыхает)
#     prompt = "Распознай чек на фото. Выдели общую сумму, категорию и позиции."
#     parsed_receipt = ai_service.analyze_image(file_url, ReceiptSchema, prompt)
#
#     # 2. Быстрая транзакция в БД
#     with db_session_ctx() as session:
#         # Ваша логика сохранения через SQLAlchemy модели...
#         session.add(NewReceipt(user_id=user_id, total=parsed_receipt.total_amount))
#         session.commit()
#
#     # 3. Отправка уведомления в Telegram...



#"Как найти API-реселлеров?"