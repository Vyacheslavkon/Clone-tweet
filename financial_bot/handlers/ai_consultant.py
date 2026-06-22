import io
from pyexpat.errors import messages

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
from financial_bot.tasks.ai import process_receipt_task, process_expense_task

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


@ai_router.message(I18nTextFilter("data entry"),AIState.waiting_for_request)
async def waiting_purchases(message: Message, state: FSMContext):

    await message.answer(_("Please tell us or write about your purchases!"))
    await state.set_state(AIState.waiting_for_receipt)


@ai_router.message(F.voice)
async def handle_voice_receipt(message: Message, session: AsyncSession ):
    user = await get_user_by_id(session, message.from_user.id)

    waiting_msg = await message.answer("🧠 I am analyzing your expenses...")

    try:
        # 2. Получаем объект голосового сообщения
        voice = message.voice

        # Защита: ограничим длину аудио (например, не больше 30 секунд),
        # чтобы пользователи не наговаривали аудиокниги
        if voice.duration > 35:
            await waiting_msg.edit_text(
                _("❌ The voice message is too long. Please dictate a shorter message (up to 30 seconds).."))
            return

        # 3. Получаем путь к файлу на серверах Telegram через Bot API
        file_info =  await message.bot.get_file(voice.file_id)

        # 4. Скачиваем файл напрямую в буфер оперативной памяти (BytesIO)
        file_buffer = io.BytesIO()
        await message.bot.download_file(file_info.file_path, file_buffer)

        # Получаем чистые байты (тип bytes)
        voice_bytes = file_buffer.getvalue()


        process_expense_task.delay(
            chat_id=message.chat.id,
            db_user_id=user.id,  # или как у вас в коде называется id пользователя
            locale=user.language_code,
            voice_bytes=voice_bytes
        )

        await message.bot.delete_message(chat_id=message.chat.id, message_id=waiting_msg.message_id)

    except Exception as e:
        logger.error(f"Ошибка при скачивании голосового сообщения: {e}", exc_info=True)
        await waiting_msg.edit_text(_("❌ Unable to process the voice message. Please try again."))



@ai_router.message(F.text)
async def handle_text_message(message: Message, session: AsyncSession):

    user = await get_user_by_id(session, message.from_user.id)

    waiting_msg = await message.answer("🧠 I am analyzing your expenses...")



    text = message.text

    process_expense_task.delay(
        chat_id=message.chat.id,
        db_user_id=user.id,  # или как у вас в коде называется id пользователя
        locale=user.language_code,
        text=text
    )

    await message.bot.delete_message(chat_id=message.chat.id, message_id=waiting_msg.message_id)

