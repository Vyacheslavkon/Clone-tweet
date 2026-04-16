from aiogram.utils.i18n import gettext as _
from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from financial_bot.filters import I18nTextFilter
from financial_bot.states.add_data_states import AddDataState
from financial_bot.keyboards.reply import change_data

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
        # implement checking value month budget
        await message.answer(_("Enter the spending limit amount"))
        await state.set_state(AddDataState.waiting_for_monthly_budget)

    if message.text == _("savings goal"):
        # implement checking value month budget
        await message.answer(_("Enter your desired savings amount"))
        await state.set_state(AddDataState.waiting_for_monthly_budget)


@router_data.message(AddDataState.waiting_for_monthly_budget)
async def saving_value_budget(session: AsyncSession, message: Message, state: FSMContext):
     pass


@router_data.message(AddDataState.waiting_for_limit_expense)
async def saving_limit_expense(session: AsyncSession, message: Message, state: FSMContext):
    # implement a value check that is not greater than month budget
    # converting an amount to a percentage
    pass


@router_data.message(AddDataState.waiting_for_savings_goal)
async def saving_value_budget(session: AsyncSession, message: Message, state: FSMContext):
    # implement a value check that is not greater than month budget
    pass