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
from financial_bot.keyboards.reply import change_data, get_main_menu
from financial_bot.repositories import add_data_for_user, get_monthly_budget
from financial_bot.schemas import AddData
from financial_bot.states.add_data_states import AddDataState

router_data = Router()


@router_data.message(I18nTextFilter("Add/change data"))
async def data_selection(message: Message, state: FSMContext):

    await message.answer(_("Please, select data type"), reply_markup=change_data())
    await state.set_state(AddDataState.waiting_for_type_data)


@router_data.message(AddDataState.waiting_for_type_data)
async def add_data(message: Message, session: AsyncSession, state: FSMContext):

    if not message.from_user:
        return

    if message.text == _("monthly budget"):
        await message.answer(_("Enter your estimated monthly budget"))
        await state.set_state(AddDataState.waiting_for_monthly_budget)

    elif message.text == _("limit expense"):
        budget = await get_monthly_budget(session, message.from_user.id)
        if budget is not None:
            await message.answer(_("Enter the spending limit amount"))
            await state.set_state(AddDataState.waiting_for_limit_expense)
        else:
            await message.answer(_("Please set a monthly budget first."))

    elif message.text == _("savings goal"):
        budget = await get_monthly_budget(session, message.from_user.id)
        if budget is not None:
            await message.answer(_("Enter your desired savings amount"))
            await state.set_state(AddDataState.waiting_for_savings_goal)
        else:
            await message.answer(_("Please set a monthly budget first."))

    else:
        await message.reply(
            _("Sorry, I didn't understand you, please use the suggested choice!"),
            reply_markup=change_data(),
        )


@router_data.message(AddDataState.waiting_for_monthly_budget)
async def saving_value_budget(
    message: Message, session: AsyncSession, state: FSMContext
):
    logger.info("Session for saving_value_budget: {}", session)

    if not message.text or not message.from_user:
        return

    try:
        value_budget = check_value_budget(message.text)
        if isinstance(value_budget, str):
            await message.answer(
                get_error_text(value_budget), reply_markup=change_data()
            )

        else:
            data = AddData(monthly_budget=value_budget)
            old_value_budget = await get_monthly_budget(session, message.from_user.id)
            await add_data_for_user(session, data, message.from_user.id)
            if old_value_budget is not None:
                await message.answer(_("Enter the spending limit amount"))
                await state.set_state(AddDataState.waiting_for_limit_expense)
            else:
                await message.answer(
                    _("The data was saved successfully."), reply_markup=get_main_menu()
                )
                await state.clear()
    except ValueError:
        await message.answer(_("Please, enter a number!"))
    except UserNotFoundError:
        await message.answer(_("Profile not found. Please type /start"))


@router_data.message(AddDataState.waiting_for_limit_expense)
async def saving_limit_expense(
    message: Message, session: AsyncSession, state: FSMContext
):
    if not message.text or not message.from_user:
        return

    try:
        budget = await get_monthly_budget(session, message.from_user.id)

        if budget is None:
            await message.answer(
                _("You don't have a budget set! Set a basic budget first.")
            )
            return

        limit_expense = transform(budget, message.text)

        if isinstance(limit_expense, str):

            await message.answer(
                get_error_text(limit_expense), reply_markup=change_data()
            )

            logger.error(limit_expense)

        else:

            data = AddData(budget_remind_percent=limit_expense)
            await add_data_for_user(session, data, message.from_user.id)
            await message.answer(
                _("The data was saved successfully."), reply_markup=get_main_menu()
            )
            await state.clear()

    except UserNotFoundError as e:
        logger.error(e)
        await message.answer(_("Profile not found. Please type /start"))
        await state.clear()


@router_data.message(AddDataState.waiting_for_savings_goal)
async def saving_goal(message: Message, session: AsyncSession, state: FSMContext):

    if not message.text or not message.from_user:
        return

    try:
        budget = await get_monthly_budget(session, message.from_user.id)

        if budget is None:
            await message.answer(
                _("You don't have a budget set! Set a basic budget first.")
            )
            return

        goal = comparison(budget, message.text)

        if isinstance(goal, str):

            await message.answer(get_error_text(goal), reply_markup=change_data())
            logger.error(goal)

        else:

            data = AddData(savings_goal=goal)
            await add_data_for_user(session, data, message.from_user.id)
            await message.answer(
                _("The data was saved successfully."), reply_markup=get_main_menu()
            )
            await state.clear()

    except UserNotFoundError as e:
        logger.error(e)
        await message.answer(_("Profile not found. Please type /start"))
        await state.clear()
