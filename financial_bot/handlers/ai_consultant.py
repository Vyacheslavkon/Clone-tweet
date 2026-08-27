import io
import os

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram.utils.i18n import gettext as _
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from redis.exceptions import RedisError

from financial_bot.filters import (
    DeleteTransactionCallback,
    I18nTextFilter,
    IsProUserFilter,
)
from financial_bot.keyboards.reply import get_main_menu, request_ai
from financial_bot.repositories import delete_check, get_user_by_id, get_user_financial_summary
from services.utils_pipelines import (render_detailed_transactions)
from services.analysis_cache import FinancialCacheService
# from financial_bot.tasks.ai import process_ai_request
from financial_bot.states.ai_states import AIState
from financial_bot.tasks.ai import process_expense_task, process_receipt_task, process_analysis_expense_task

redis_url = os.getenv("ANALYSIS_CACHE_REDIS")
if not redis_url:
    raise ValueError("CRITICAL: ANALYSIS_CACHE_REDIS environment variable is not set!")

ai_router = Router()


@ai_router.message(I18nTextFilter("AI"), IsProUserFilter())
async def waiting_for_request(message: Message, state: FSMContext):
    await message.answer(_("Please, select request!"), reply_markup=request_ai())
    await state.set_state(AIState.waiting_for_request)


@ai_router.message(I18nTextFilter("AI"))
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

    await message.answer(_("Please tell me about your purchases!"))
    await state.set_state(AIState.waiting_for_receipt)


@ai_router.message(F.voice, AIState.waiting_for_receipt)
async def handle_voice_receipt(message: Message, session: AsyncSession, state: FSMContext):
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

        await state.clear()

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



@ai_router.callback_query(DeleteTransactionCallback.filter())
async def delete_batch_handler(
    callback: CallbackQuery,
    callback_data: DeleteTransactionCallback,
    session: AsyncSession,
    cache_service: FinancialCacheService

):
    user = await get_user_by_id(session, callback.from_user.id)

    result = await delete_check(session, callback_data.batch_id)


    try:
        await cache_service.invalidate_user_cache(user_id=user.id)
        logger.info("Successfully invalidated cache for user: %s via manual entry", user.id)
    except RedisError as redis_err:
        # Ловим ТОЛЬКО конкретные сетевые проблемы с Redis
        logger.error(
            "Non-critical error: Failed to clear Redis cache during manual entry for user %s: %s",
            user.id, redis_err
        )

    if result:
        if isinstance(callback.message, Message):
            await callback.message.edit_text(
                _("❌ The record has been cancelled and removed from the database.")
            )
    else:
        if isinstance(callback.message, Message):
            await callback.answer(_("Record not found."), show_alert=True)

            await callback.message.edit_reply_markup(reply_markup=None)



@ai_router.message(I18nTextFilter("weekly data analysis", "monthly data analysis"))
async def handle_analytics_request(message: Message, state: FSMContext):

    if not message.from_user:
        return


    weekly_text = _("weekly data analysis")
    monthly_text = _("monthly data analysis")

    days_mapping = {
        weekly_text: 7,
        monthly_text: 30
    }

    user_text = message.text

    days = days_mapping[user_text]
    now = datetime.now(timezone.utc)

    if days == 7:
        days_passed = now.weekday() + 1
        if days_passed < 3:
            await state.clear()

            await message.answer(
                _("📊 *The period is too short to analyze the current week!* \n"
                  "We can only analyze the week starting from Wednesday, when enough spendings accumulate. "
                  "Please check back later! 🗓"),
                reply_markup=get_main_menu()
            )

            return

    elif days == 30:
        days_passed = now.day
        if days_passed < 10:
            await state.clear()

            await message.answer(
                _("📈 *It’s too early for monthly analytics!* \n"
                  "A reliable monthly analysis requires at least 10 days of data (available from the 10th). "
                  "Right now, try checking your weekly analytics instead! 📅"),
                reply_markup=get_main_menu()
            )

            return



    process_analysis_expense_task.delay(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        days=days,

    )

    await state.clear()

    await message.answer(
        _("🤖 *AI is analyzing your spending patterns...* \nIt will take five or ten seconds.",
          ), reply_markup=get_main_menu())



@ai_router.callback_query(F.data.startswith("show_detailed_report:"))
async def handle_show_detailed_report(callback: CallbackQuery, session: AsyncSession):

    days = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    user = await get_user_by_id(session, user_id)

    data = await get_user_financial_summary(session, user.id, days, user)

    report_text = render_detailed_transactions(data, _)

    if len(report_text) <= 4000:

        await callback.message.answer(text=report_text, parse_mode="HTML")

    else:

        file_buffer = io.BytesIO(report_text.encode('utf-8'))
        file_buffer.seek(0)

        filename = f"financial_report_{days}_days.txt"
        document = BufferedInputFile(file_buffer.read(), filename=filename)


        await callback.message.answer_document(
            document=document,
            caption=_(
                "🧾 <b>Your detailed report exceeded Telegram's message length limit.</b>\nI’ve packed the entire transaction history into this file! 📁")
        )

    await callback.answer()