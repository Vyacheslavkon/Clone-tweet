from aiogram.utils.i18n import gettext as _
from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import InvalidOperation
from loguru import logger

from financial_bot.filters import I18nTextFilter
from financial_bot.states.add_data_states import AddDataState
from financial_bot.keyboards.reply import change_data
from financial_bot.repositories import add_data_for_user, get_monthly_budget
from financial_bot.schemas import AddData
from financial_bot.exceptions import UserNotFoundError
from financial_bot.handlers.utils import transform, get_error_text


router_data = Router()


@router_data.message(I18nTextFilter("Add/change data"))
async def data_selection(message: Message, state: FSMContext):

    await message.answer(_("Please, select data type"), reply_markup=change_data())
    await state.set_state(AddDataState.waiting_for_type_data)


@router_data.message(AddDataState.waiting_for_type_data)
async def add_data(message: Message, session: AsyncSession, state: FSMContext):

    if message.text == _("monthly budget"):
        await message.answer(_("Enter your estimated monthly budget"))
        await state.set_state(AddDataState.waiting_for_monthly_budget)

    if message.text == _("limit expense"):
        budget = get_monthly_budget(session, message.from_user.id)
        if budget is not None:
            await message.answer(_("Enter the spending limit amount"))
            await state.set_state(AddDataState.waiting_for_monthly_budget)
        else:
            await message.answer("Please set a monthly budget first.")

    if message.text == _("savings goal"):
        budget = get_monthly_budget(session, message.from_user.id)
        if budget is not None:
            await message.answer(_("Enter your desired savings amount"))
            await state.set_state(AddDataState.waiting_for_monthly_budget)
        else:
            await message.answer("Please set a monthly budget first.")


@router_data.message(AddDataState.waiting_for_monthly_budget)
async def saving_value_budget(session: AsyncSession, message: Message, state: FSMContext):

     try:
         data = AddData(monthly_budget=message.text)
         await add_data_for_user(session, data, message.from_user.id)
         await message.answer("The budget was successfully saved.")
         await state.clear()
     except ValueError:
         await message.answer("Please, enter a number!")
     except UserNotFoundError:
         await message.answer("Profile not found. Please type /start")


@router_data.message(AddDataState.waiting_for_limit_expense)
async def saving_limit_expense(session: AsyncSession, message: Message, state: FSMContext):
    try:
        budget = await get_monthly_budget(session, message.from_user.id)
        limit_expense = transform(budget, message.text)

        if isinstance(limit_expense, str):

            await message.answer(get_error_text(limit_expense))
            logger.error(limit_expense)

        else:



            data = AddData(budget_remind_percent=limit_expense)
            await add_data_for_user(session, data, message.from_user.id)
            await message.answer("The spending limit was successfully saved.")
            await state.clear()

    except UserNotFoundError as e:
        logger.error(e)
        await message.answer("Profile not found. Please type /start")
        await state.clear()


@router_data.message(AddDataState.waiting_for_savings_goal)
async def saving_value_budget(session: AsyncSession, message: Message, state: FSMContext):
    # implement a value check that is not greater than month budget
    pass