from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from financial_bot.exceptions import UserNotFoundError
from financial_bot.filters import I18nTextFilter
from financial_bot.handlers.utils import (
    check_value_budget,
    comparison,
    get_error_text,
    transform,
)
from financial_bot.keyboards.reply import request_ai
from financial_bot.repositories import get_user_by_id
from financial_bot.tasks.ai import process_ai_request
from financial_bot.states.ai_states import AIState

ai_router = Router()

@ai_router.message("AI")
async def waiting_for_request(message: Message, state: FSMContext, session: AsyncSession):

    user = await get_user_by_id(session, message.from_user.id)

    if user and  user.subscription_type == "pro":
        await message.answer(_("Please, select request!"), reply_markup=request_ai())
        await state.set_state(AIState.waiting_for_request)

    else:
        await message.answer(_("Sorry, you need a PRO subscription to use AI."))


@ai_router.message()
async def weekly_analysis(message: Message):
    # Отправляем заглушку пользователю
    placeholder = await message.answer(_("🤖 Wait a second, I'm analyzing your finances..."))

    # Write to text for the request Ai

    # Триггерим Celery задачу (передаем .delay() или .apply_async())
    process_ai_request.apply_async(
        args=[message.chat.id, placeholder.message_id, message.text],
        queue="ai_tasks"
    )