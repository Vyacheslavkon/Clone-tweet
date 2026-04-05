from aiogram.types import Message, CallbackQuery
from aiogram import Router, F
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils.i18n import gettext as _

from financial_bot.repositories import get_user_by_id, create_user
from financial_bot.keyboards.reply import get_main_menu
from financial_bot.schemas import CreateUser


router_st = Router()


@router_st.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):

    user = await get_user_by_id(session, message.from_user.id)

    if not user:
        new_user = CreateUser(
            tg_id=message.from_user.id,
            first_name=message.from_user.first_name,
            language_code=message.from_user.language_code
        )

        await create_user(session, new_user)
        await message.answer( _("Hello, {name}! Glad to meet you!")
                              .format(name=message.from_user.first_name),
                              reply_markup=get_main_menu())

    else:

        await message.answer(_("Glad to see you {name}! Your balance: {balance}")
                             .format(name=message.from_user.first_name),
                             reply_markup=get_main_menu())


