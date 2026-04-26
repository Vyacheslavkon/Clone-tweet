from typing import Union

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.i18n import gettext as _
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from financial_bot.filters import I18nTextFilter
from financial_bot.keyboards.inline import get_category, get_description, get_type
from financial_bot.keyboards.reply import get_main_menu
from financial_bot.repositories import add_transaction, get_user_by_id
from financial_bot.schemas import AddTransaction
from financial_bot.states.amount_states import AmountState

router_tr = Router()


@router_tr.callback_query(F.data == "back")
async def go_back(callback: CallbackQuery, state: FSMContext):

    if not callback.message or not isinstance(callback.message, Message):
        await callback.answer()
        return

    current_state = await state.get_state()

    if current_state == AmountState.waiting_for_amount.state:
        await state.clear()
        await callback.message.delete()

        await callback.message.answer(
            _("Please enter the amount!"), reply_markup=get_main_menu()
        )

    elif current_state == AmountState.waiting_for_type.state:
        await state.set_state(AmountState.waiting_for_amount)

        await callback.message.delete()

        await callback.message.answer(
            _("Please enter the amount!"), reply_markup=get_main_menu()
        )

    elif current_state == AmountState.waiting_for_cat.state:
        await state.set_state(AmountState.waiting_for_type)
        await callback.message.edit_text(_("Select type"), reply_markup=get_type())

    elif current_state == AmountState.waiting_for_description.state:
        await state.set_state(AmountState.waiting_for_cat)
        dict_data = await state.get_data()
        type_transaction = str(dict_data.get("type", "expense"))
        await callback.message.edit_text(
            _("Select category"), reply_markup=get_category(type_transaction)
        )

    await callback.answer()


@router_tr.message(I18nTextFilter("Enter amount"))
async def new_amount(message: Message, state: FSMContext):

    await message.answer(_("Please enter the amount!"))
    await state.set_state(AmountState.waiting_for_amount)


@router_tr.message(AmountState.waiting_for_amount)
async def process_amount_input(message: Message, state: FSMContext):

    if not message.text:
        return await message.answer(_("Please send a text message with a number!"))

    try:
        amount = float(message.text.replace(",", "."))
        await state.update_data(amount=amount)

        kb = get_type()
        await message.answer(_("Select type:"), reply_markup=kb)

        await state.set_state(AmountState.waiting_for_type)
    except ValueError:
        return await message.answer(_("Enter a numeric value!"))


@router_tr.callback_query(F.data.startswith("type"), AmountState.waiting_for_type)
async def type_amount(callback: CallbackQuery, state: FSMContext):

    if not callback.data or not isinstance(callback.message, Message):
        await callback.answer()
        return

    selected_type = callback.data.split("_")[1]
    await state.update_data(type=selected_type)
    await callback.message.edit_text(
        _("Select category"), reply_markup=get_category(selected_type)
    )
    await callback.answer()
    await state.set_state(AmountState.waiting_for_cat)


@router_tr.callback_query(F.data.startswith("cat"), AmountState.waiting_for_cat)
async def category_amount(callback: CallbackQuery, state: FSMContext):

    if not callback.data or not isinstance(callback.message, Message):
        await callback.answer()
        return

    selected_cat = callback.data.split("_")[1]

    await state.update_data(category=selected_cat)
    await callback.message.edit_text(
        _("Write a comment"), reply_markup=get_description()
    )
    await callback.answer()
    await state.set_state(AmountState.waiting_for_description)


@router_tr.callback_query(
    F.data == "skip_description", AmountState.waiting_for_description
)
async def end_with_callback(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):

    await state.update_data(description=None)
    await save_to_db_and_finish(callback, state, session, callback.from_user.id)


@router_tr.message(AmountState.waiting_for_description)
async def end_with_message(message: Message, state: FSMContext, session: AsyncSession):

    if not message.from_user:
        return

    await state.update_data(description=message.text)
    await save_to_db_and_finish(message, state, session, message.from_user.id)


async def save_to_db_and_finish(
    event: Union[Message, CallbackQuery],
    state: FSMContext,
    session: AsyncSession,
    tg_id: int,
):

    data = await state.get_data()
    user = await get_user_by_id(session, tg_id)

    if not user:
        logger.error("User with id {} not found in database", tg_id)
        return

    data["user_id"] = user.id

    try:
        transaction = AddTransaction(**data)

        await add_transaction(session, transaction.model_dump())

        text = _("Data saved successfully!")
        if isinstance(event, CallbackQuery):
            if isinstance(event.message, Message):
                await event.message.answer(text, reply_markup=get_main_menu())
            await event.answer()
        else:
            await event.answer(text, reply_markup=get_main_menu())

        await state.clear()
    except SQLAlchemyError as e:

        logger.error("Error saving: {}", e)
