from aiogram.types import Message
from aiogram import Router
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from financial_bot.repositories import get_user_by_id


router_st = Router()


@router_st.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):
    user = await get_user_by_id(session, message.from_user.id)

    if not user:
        await message.answer("You are not registered!")
        return

    await message.answer(f"Glad to see you, {user.first_name}!")