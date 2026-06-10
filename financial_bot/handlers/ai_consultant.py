import io

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from financial_bot.filters import I18nTextFilter
from financial_bot.exceptions import UserNotFoundError
from financial_bot.filters import I18nTextFilter, IsProUserFilter
from financial_bot.repositories import get_user_by_id
from financial_bot.handlers.utils import (
    check_value_budget,
    comparison,
    get_error_text,
    transform,
)
from financial_bot.keyboards.reply import request_ai, get_main_menu
#from financial_bot.tasks.ai import process_ai_request
from financial_bot.states.ai_states import AIState
from financial_bot.tasks.ai import process_receipt_task

ai_router = Router()

@ai_router.message(F.text == "AI", IsProUserFilter())
async def waiting_for_request(message: Message, state: FSMContext):
    await message.answer(_("Please, select request!"), reply_markup=request_ai())
    await state.set_state(AIState.waiting_for_request)


@ai_router.message(F.text == "AI")
async def ai_access_denied(message: Message):
    await message.answer(_("Sorry, you need a PRO subscription to use AI."))


#@ai_router.message(F.text == "check",AIState.waiting_for_request)
@ai_router.message(I18nTextFilter("check"),AIState.waiting_for_request)
async def waiting_check(message: Message, state: FSMContext):

    await message.answer(_("Please send me a photo of the receipt!"))
    await state.set_state(AIState.waiting_for_receipt)


@ai_router.message(F.photo, AIState.waiting_for_receipt)
async def handle_receipt_photo(message: Message, state: FSMContext, session: AsyncSession):

    user = await get_user_by_id(session, message.from_user.id)

    if not user:
        logger.error("User with id {} not found in database", message.from_user.id)
        return

    user_locale = user.language_code
    photo = message.photo[-1]

    # 2. Запрашиваем инфо о файле СРАЗУ в основном цикле бота (to improve productivity)
    #file_info = await message.bot.get_file(photo.file_id)
    #telegram_file_path = file_info.file_path

    file_in_io = io.BytesIO()
    await message.bot.download(photo, destination=file_in_io)
    file_bytes = file_in_io.getvalue()

    process_receipt_task.delay(
        chat_id=message.chat.id,
        db_user_id=user.id,
        #file_id=photo.file_id,
        locale=user_locale,
        image_bytes=file_bytes
        #file_path = file_info.file_path  # Передаем путь(to improve productivity)
    )

    await message.answer("⏳  Чек принят на анализ, это займет несколько секунд...",
                         reply_markup=get_main_menu())
    await state.clear()


"""
import os
from aiogram import Router, F
from aiogram.types import Message

# Импортируем вашу Celery-таску (укажите ваш правильный путь импорта)
from pipelines import process_receipt_task 

router = Router()

# Создаем папку для чеков, если её еще нет
# В Docker эта папка должна быть общей (Volume) для бота и Celery
MEDIA_DIR = "/app/media/receipts"
os.makedirs(MEDIA_DIR, exist_ok=True)


@router.message(F.photo)
async def handle_receipt_photo(message: Message):
    ""Хэндлер принимает фото, сохраняет на диск и отправляет путь в Celery.""
    
    # 1. Берем самое последнее фото из списка (оно всегда самого лучшего качества)
    photo = message.photo[-1]
    
    # 2. Получаем объект файла из Telegram (там содержится file_path для скачивания)
    file_info = await message.bot.get_file(photo.file_id)
    telegram_file_path = file_info.file_path # Внутренний путь на серверах TG (например, photos/file_0.jpg)

    # 3. Формируем уникальное имя файла для нашего локального диска
    # Используем file_id или ID сообщения, чтобы имена не повторялись
    file_extension = telegram_file_path.split('.')[-1] # Получаем расширение (jpg, png)
    local_file_name = f"user_{message.from_user.id}_{message.message_id}.{file_extension}"
    
    # Полный абсолютный путь на нашем сервере
    absolute_local_path = os.path.join(MEDIA_DIR, local_file_name)

    # 4. Скачиваем файл из Telegram на наш локальный диск
    await message.bot.download_file(
        file_path=telegram_file_path, 
        destination=absolute_local_path
    )

    # Имитируем создание транзакции в БД, чтобы получить её ID
    # (Здесь должен быть ваш код создания пустой транзакции на SQLAlchemy)
    mock_transaction_id = 42 

    # 5. Передаем локальный путь в Celery-таску через .delay()
    process_receipt_task.delay(
        user_id=message.from_user.id,
        transaction_id=mock_transaction_id,
        image_path=absolute_local_path # Улетает простая строка!
    )

    # 6. Отвечаем пользователю, что чек ушел на обработку
    await message.answer(
        "🧾 Ваша квитанция принята на обработку! "
        "Нейросеть уже разбирает товары, это займет около 10-15 секунд."
    )


"""