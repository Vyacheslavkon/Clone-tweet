from typing import Union

from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram import F
from aiogram import Router
from aiogram.filters import Command
from aiogram.utils.i18n import gettext as _
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from financial_bot.repositories import add_transaction
from financial_bot.schemas import AddTransaction
from financial_bot.states.amount_states import AmountState
from financial_bot.keyboards.inline import get_type, get_category, get_description
from financial_bot.keyboards.reply import get_main_menu

router_tr = Router()

@router_tr.callback_query(F.data == "back")
async def go_back(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()

    if current_state == AmountState.waiting_for_amount.state:
        await state.clear()
        await callback.message.edit_text(_("Main menu"), reply_markup=get_main_menu())

    elif current_state == AmountState.waiting_for_type.state:
        await state.set_state(AmountState.waiting_for_amount)
        await callback.message.edit_text(_("Please enter the amount!"), reply_markup=get_main_menu())

    elif current_state == AmountState.waiting_for_cat.state:
        await state.set_state(AmountState.waiting_for_type)
        await callback.message.edit_text(_("Select type"), reply_markup=get_type())

    elif current_state == AmountState.waiting_for_description.state:
        await state.set_state(AmountState.waiting_for_cat)
        await callback.message.edit_text(_("Select category"), reply_markup=get_main_menu())

    await callback.answer()



@router_tr.message(F.text == _("Enter amount"))
async def new_amount(message: Message, state: FSMContext):

    await message.answer( _("Please enter the amount!"))
    await state.set_state(AmountState.waiting_for_amount)


@router_tr.message(AmountState.waiting_for_amount)
async def process_amount_input(message: Message, state: FSMContext):

    await state.update_data(amount=message.text)

    kb = get_type()
    await message.answer(_("Select type:"), reply_markup=kb)

    await state.set_state(AmountState.waiting_for_type)


@router_tr.callback_query(F.data.startswith(_("type")), AmountState.waiting_for_type)
async def type_amount(callback: CallbackQuery, state: FSMContext):

    selected_type = callback.data.split("_")[1]
    await state.update_data(type_amt=selected_type)
    await callback.message.edit_text(_("Select category"), reply_markup=get_category())
    await callback.answer()
    await state.set_state(AmountState.waiting_for_cat)

@router_tr.callback_query(F.data.startwith(_("cat")), AmountState.waiting_for_cat)
async def category_amount(callback: CallbackQuery, state: FSMContext):

    selected_cat = callback.data.split("_")[1]

    await state.update_data(cat_amt=selected_cat)
    await callback.message.edit_text(_("Write a comment"), reply_markup=get_description())
    await callback.answer()
    await state.set_state(AmountState.waiting_for_description)


# 1. Хендлер для кнопки "Пропустить/Без описания"
@router_tr.callback_query(F.data == "skip_description", AmountState.waiting_for_description)
async def end_with_callback(callback: CallbackQuery, state: FSMContext):
    # Устанавливаем пустое описание или None
    await state.update_data(description=None)
    await save_to_db_and_finish(callback, state) # Выносим логику сохранения

# 2. Хендлер для ТЕКСТОВОГО ввода описания
@router_tr.message(AmountState.waiting_for_description)
async def end_with_message(message: Message, state: FSMContext, session: AsyncSession):
    # Сохраняем реальный текст от пользователя
    await state.update_data(description=message.text)
    await save_to_db_and_finish(message, state)


# Общая функция сохранения
async def save_to_db_and_finish(event: Union[Message, CallbackQuery], state: FSMContext):
    data = await state.get_data()


    # Предположим, у вас есть Pydantic модель TransactionModel
    # Если нет, просто передавайте data в функцию
    try:
        transaction = AddTransaction(**data)

        res = add_transaction(**transaction.model_dump())

        text = _("Data saved successfully!")
        if isinstance(event, CallbackQuery):
            await event.message.answer(text)
            await event.answer()
        else:
            await event.answer(text)

        await state.clear()
    except Exception as e:
        # Логируем ошибку, если данные в data не соответствуют аргументам add_transaction

        logger.error(f"Error saving: {e}")




# @router_tr.callback_query(F.data == "description", AmountState.waiting_for_description)
# async def end(callback: CallbackQuery, state: FSMContext):
#
#     selected_cat = callback.data
#
#     await state.update_data(description=selected_cat)
#
#     data = await state.get_data()
#
#     transaction = AddTransaction(**data)
#
#     res = add_transaction(**transaction.model_dump())
#     await callback.answer(_("Data saved successfully!"))
#     await state.clear()
