from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram import F
from aiogram import Router
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from financial_bot.repositories import add_transaction
from financial_bot.schemas import AddTransaction
from financial_bot.states.amount_states import AmountState
from financial_bot.keyboards.inline import get_type
from financial_bot.keyboards.reply import get_main_menu

router_tr = Router()

@router_tr.callback_query(F.data == "back")
async def go_back(callback: CallbackQuery, state: FSMContext, lp: dict):
    current_state = await state.get_state()

    if current_state == AmountState.waiting_for_amount.state:
        await state.clear()
        await callback.message.edit_text(lp["main_menu"], reply_markup=get_main_menu())

    elif current_state == AmountState.waiting_for_type.state:
        # Если были на городе — возвращаемся к возрасту
        await state.set_state(AmountState.waiting_for_amount)
        await callback.message.edit_text("Введите ваш возраст:", reply_markup=get_main_menu())

    await callback.answer()
    # finalize


@router_tr.message(F.text == "Enter amount")
async def new_amount(message: Message, lp: dict, state: FSMContext):

    await message.answer(lp["entering_amount"])
    await state.set_state(AmountState.waiting_for_amount)

@router_tr.callback_query(F.data == "", AmountState.waiting_for_amount)
async def type_amount(callback: CallbackQuery, lp: dict, state: FSMContext):

   # await state.update_data(amount=message.text)
    await callback.answer(lp["type_amt"])
    await state.set_state(AddTransaction.type)
