import asyncio
from dotenv import load_dotenv

from services.celery_app import app
from services.pipelines import async_process_receipt

load_dotenv()

celery_app = app


@celery_app.task(name="tasks.process_receipt")
def process_receipt_task(chat_id: int, db_user_id: int, file_id: str):
    """Синхронная обертка Celery, запускающая асинсохронный event loop"""
    asyncio.run(async_process_receipt(chat_id, db_user_id, file_id))


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
