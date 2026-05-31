# import asyncio
# from celery import Celery
# from aiogram import Bot
# from sqlalchemy.ext.asyncio import create_async_io_engine, async_sessionmaker
#
# from config import (
#     REDIS_URL, POSTGRES_ASYNC_URL, BOT_TOKEN,
#     PROXY_API_KEY, PROXY_BASE_URL
# )
# from services import AIService
# from schemas import ReceiptAnalysisSchema
# from prompts import RECEIPT_SYSTEM_PROMPT
# from database_methods import save_receipt_to_db  # Функция, которую мы писали ранее
#
# # 1. Инициализация Celery
# celery_app = Celery("financial_bot_tasks", broker=REDIS_URL, backend=REDIS_URL)
#
# # 2. Настройка асинхронного движка SQLAlchemy для Воркера
# async_engine = create_async_io_engine(POSTGRES_ASYNC_URL, echo=False)
# AsyncSessionLocal = async_sessionmaker(bind=async_engine, expire_on_commit=False)
#
#
# # 3. Вспомогательная асинхронная функция, где происходит вся магия
# async def _async_process_receipt(chat_id: int, db_user_id: int, file_id: str):
#     # Инициализируем бота и ваш универсальный AI-сервис
#     bot = Bot(token=BOT_TOKEN)
#     ai_service = AIService(api_key=PROXY_API_KEY, base_url=PROXY_BASE_URL)
#
#     async with AsyncSessionLocal() as session:
#         try:
#             # Получаем путь к файлу на серверах Telegram
#             file_info = await bot.get_file(file_id)
#             file_url = f"https://telegram.org{BOT_TOKEN}/{file_info.file_path}"
#
#             # Вызываем ваш асинхронный метод из класса AIService
#             analysis_result: ReceiptAnalysisSchema = await ai_service.analyze_image(
#                 image_url=file_url,
#                 response_schema=ReceiptAnalysisSchema,
#                 system_prompt=RECEIPT_SYSTEM_PROMPT
#             )
#
#             # Сохраняем транзакцию и позиции чека в PostgreSQL
#             await save_receipt_to_db(
#                 session=session,
#                 user_id=db_user_id,
#                 analysis_result=analysis_result,
#                 photo_url=file_url,
#                 raw_text=str(analysis_result.model_dump())  # или любой кастомный текст
#             )
#
#             # Формируем красивый ответ
#             msg_text = (
#                 f"✅ **Чек успешно обработан!**\n\n"
#                 f"🏬 Магазин: {analysis_result.description or 'Неизвестно'}\n"
#                 f"💰 Сумма: {analysis_result.total_amount} {analysis_result.currency}\n"
#                 f"🗂 Категория: {analysis_result.category}\n\n"
#                 f"🧾 Позиции добавлены в вашу детальную статистику."
#             )
#             await bot.send_message(chat_id=chat_id, text=msg_text, parse_mode="Markdown")
#
#         except Exception as e:
#             # Здесь используем ваш loguru для логирования ошибок в Docker-контейнере
#             from loguru import logger
#             logger.error(f"Ошибка при обработке чека для user {db_user_id}: {e}")
#
#             await bot.send_message(
#                 chat_id=chat_id,
#                 text="❌ К сожалению, не удалось распознать чек. Пожалуйста, убедитесь, что фото четкое, и попробуйте снова."
#             )
#         finally:
#             # Закрываем сессию бота
#             await bot.session.close()
#
#
# # 4. Сама Celery-таска (Точка входа)
# @celery_app.task(name="tasks.process_receipt")
# def process_receipt_task(chat_id: int, db_user_id: int, file_id: str):
#     """Синхронная обертка Celery, запускающая асинсохронный event loop"""
#     asyncio.run(_async_process_receipt(chat_id, db_user_id, file_id))


# Предыдущие шаги проверки подписки пройдены, юзер прислал фото
# @ai_router.message(AIState.waiting_for_receipt, F.photo)
# async def handle_receipt_photo(message: Message, state: FSMContext, session: AsyncSession):
#     # Получаем внутренний id из БД (мы уже обсудили, почему он нужен)
#     user = await get_user_by_id(session, message.from_user.id)
#
#     # Берем самое качественное фото из массива
#     photo = message.photo[-1]
#
#     # Отправляем в Celery. За счет .delay() метод срабатывает мгновенно
#     from tasks import process_receipt_task
#     process_receipt_task.delay(
#         chat_id=message.chat.id,
#         db_user_id=user.id,  # Внутренний ID из базы данных
#         file_id=photo.file_id  # ID файла в Telegram
#     )
#
#     await message.answer("⏳ Магия ИИ началась! Чек принят на анализ, это займет несколько секунд...")
#     await state.clear()  # Сбрасываем состояние
