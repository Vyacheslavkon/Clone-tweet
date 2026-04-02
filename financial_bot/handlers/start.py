from aiogram.types import Message, CallbackQuery
from aiogram import Router, F
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from financial_bot.repositories import get_user_by_id, create_user
from financial_bot.keyboards.reply import get_main_menu
from financial_bot.schemas import CreateUser


router_st = Router()


@router_st.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession, lp: dict):

    text = lp['greet'].format(name=message.from_user.first_name, balance=0)
    text_new_user = lp["greet_new_user"].format(name=message.from_user.first_name)
    user = await get_user_by_id(session, message.from_user.id)

    if not user:
        new_user = CreateUser(
            tg_id=message.from_user.id,
            first_name=message.from_user.first_name,
            language_code=message.from_user.language_code
        )

        await create_user(session, new_user)
        await message.answer(text_new_user, reply_markup=get_main_menu())

    else:

        await message.answer(text, reply_markup=get_main_menu())


