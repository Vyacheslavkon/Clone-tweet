from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

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


@ai_router.message(F.text == "check",AIState.waiting_for_request)
async def waiting_check(message: Message, state: FSMContext):

    await message.answer(_("Please send me a photo of the receipt!"))
    await state.set_state(AIState.waiting_for_receipt)


@ai_router.message(F.photo, AIState.waiting_for_receipt)
async def handle_receipt_photo(message: Message, state: FSMContext, session: AsyncSession):

    user = await get_user_by_id(session, message.from_user.id)

    photo = message.photo[-1]

    # 2. Запрашиваем инфо о файле СРАЗУ в основном цикле бота (to improve productivity)
    #file_info = await message.bot.get_file(photo.file_id)

    process_receipt_task.delay(
        chat_id=message.chat.id,
        db_user_id=user.id,
        file_id=photo.file_id
        #file_path = file_info.file_path  # Передаем путь(to improve productivity)
    )

    await message.answer("⏳  Чек принят на анализ, это займет несколько секунд...",
                         reply_markup=get_main_menu())
    await state.clear()