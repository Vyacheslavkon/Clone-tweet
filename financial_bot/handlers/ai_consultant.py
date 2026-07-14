import io

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.i18n import gettext as _
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from financial_bot.filters import (
    DeleteTransactionCallback,
    I18nTextFilter,
    IsProUserFilter,
)
from financial_bot.keyboards.reply import get_main_menu, request_ai
from financial_bot.repositories import delete_check, get_user_by_id

# from financial_bot.tasks.ai import process_ai_request
from financial_bot.states.ai_states import AIState
from financial_bot.tasks.ai import process_expense_task, process_receipt_task

ai_router = Router()


@ai_router.message(F.text == "AI", IsProUserFilter())
async def waiting_for_request(message: Message, state: FSMContext):
    await message.answer(_("Please, select request!"), reply_markup=request_ai())
    await state.set_state(AIState.waiting_for_request)


@ai_router.message(F.text == "AI")
async def ai_access_denied(message: Message):
    await message.answer(_("Sorry, you need a PRO subscription to use AI."))


# @ai_router.message(F.text == "check",AIState.waiting_for_request)
@ai_router.message(I18nTextFilter("check"), AIState.waiting_for_request)
async def waiting_check(message: Message, state: FSMContext):

    await message.answer(_("Please send me a photo of the receipt!"))
    await state.set_state(AIState.waiting_for_receipt)


@ai_router.message(F.photo, AIState.waiting_for_receipt)
async def handle_receipt_photo(
    message: Message, state: FSMContext, session: AsyncSession
):
    if not message.from_user:
        return

    user = await get_user_by_id(session, message.from_user.id)

    if not user:
        logger.error("User with id {} not found in database", message.from_user.id)
        return

    user_locale = user.language_code

    if not message.photo:
        return

    photo = message.photo[-1]

    # 2. Запрашиваем инфо о файле СРАЗУ в основном цикле бота (to improve productivity)
    # file_info = await message.bot.get_file(photo.file_id)
    # telegram_file_path = file_info.file_path

    file_in_io = io.BytesIO()

    if not message.bot:
        return

    await message.bot.download(photo, destination=file_in_io)
    file_bytes = file_in_io.getvalue()

    process_receipt_task.delay(
        chat_id=message.chat.id,
        db_user_id=user.id,
        # file_id=photo.file_id,
        locale=user_locale,
        image_bytes=file_bytes,
        # file_path = file_info.file_path  # Передаем путь(to improve productivity)
    )

    await message.answer(
        "⏳  Чек принят на анализ, это займет несколько секунд...",
        reply_markup=get_main_menu(),
    )
    await state.clear()


@ai_router.message(I18nTextFilter("data entry"), AIState.waiting_for_request)
async def waiting_purchases(message: Message, state: FSMContext):

    await message.answer(_("Please tell us or write about your purchases!"))
    await state.set_state(AIState.waiting_for_receipt)


@ai_router.message(F.voice)
async def handle_voice_receipt(message: Message, session: AsyncSession):
    if not message.from_user:
        return

    user = await get_user_by_id(session, message.from_user.id)

    if not user:
        await message.answer(_("User not found. Please enter /start."))
        return

    waiting_msg = await message.answer(_("🧠 I am analyzing your expenses..."))

    try:
        voice = message.voice

        if not voice or not message.bot:
            return

        if voice.duration > 35:
            await waiting_msg.edit_text(
                _(
                    "❌ The voice message is too long. Please dictate a shorter message (up to 30 seconds).."
                )
            )
            return

        file_info = await message.bot.get_file(voice.file_id)

        file_buffer = io.BytesIO()

        if not file_info.file_path:
            await message.answer(
                "Unfortunately, it was not possible to obtain the path for downloading the file."
            )
            return

        await message.bot.download_file(file_info.file_path, file_buffer)

        voice_bytes = file_buffer.getvalue()

        process_expense_task.delay(
            chat_id=message.chat.id,
            db_user_id=user.id,
            locale=user.language_code,
            voice_bytes=voice_bytes,
        )

        await message.bot.delete_message(
            chat_id=message.chat.id, message_id=waiting_msg.message_id
        )

        await message.answer(
            _(
                "⏳ Background analysis started. I’ll send the result in a couple of seconds; in the meantime, you can continue working:"
            ),
            reply_markup=get_main_menu(),
        )

    except Exception as e:  # noqa: PIE786
        logger.error("Error downloading voice message: {error}", error=e, exc_info=True)
        await waiting_msg.edit_text(
            _("❌ Unable to process the voice message. Please try again."),
            reply_markup=get_main_menu(),
        )


@ai_router.message(F.text)
async def handle_text_message(message: Message, session: AsyncSession):
    if not message.from_user:
        return

    user = await get_user_by_id(session, message.from_user.id)

    if not user:
        await message.answer(_("User not found. Please enter /start."))
        return

    waiting_msg = await message.answer(_("🧠 I am analyzing your expenses..."))

    text = message.text

    process_expense_task.delay(
        chat_id=message.chat.id,
        db_user_id=user.id,  # или как у вас в коде называется id пользователя
        locale=user.language_code,
        text=text,
    )

    if message.bot:
        await message.bot.delete_message(
            chat_id=message.chat.id, message_id=waiting_msg.message_id
        )


@ai_router.callback_query(DeleteTransactionCallback.filter())
async def delete_batch_handler(
    callback: CallbackQuery,
    callback_data: DeleteTransactionCallback,
    session: AsyncSession,
):

    result = await delete_check(session, callback_data.batch_id)
    if result:
        if isinstance(callback.message, Message):
            await callback.message.edit_text(
                _("❌ The record has been cancelled and removed from the database.")
            )
    else:
        if isinstance(callback.message, Message):
            await callback.answer(_("Record not found."), show_alert=True)

            await callback.message.edit_reply_markup(reply_markup=None)
