from aiogram.types import Message, CallbackQuery
from aiogram import Router, F
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from financial_bot.repositories import get_user_by_id
from financial_bot.keyboards.inline import get_confirm_kb
from financial_bot.keyboards.reply import get_main_menu


router_st = Router()


# @router_st.message(Command("start"))
# async def cmd_start(message: Message, session: AsyncSession):
#     user = await get_user_by_id(session, message.from_user.id)
#
#     if not user:
#         await message.answer("You are not registered!", reply_markup=get_confirm_kb())
#         #return
#
#     await message.answer(f"Glad to see you, {user.first_name}!")

@router_st.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Welcome to capital bot!",
        reply_markup=get_main_menu() # Прикрепляем обычную клавиатуру
    )

# @router_st.callback_query(F.data == "confirm_tx")
# async def handle_confirm(callback: CallbackQuery):
#     await callback.answer("Транзакция подтверждена!") # Всплывающее уведомление
#     await callback.message.edit_text("Готово ✅") # Редактируем сообщение
