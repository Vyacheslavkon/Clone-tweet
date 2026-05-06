import os

from aiogram.types import Message, CallbackQuery
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv

from financial_bot.filters import I18nTextFilter

set_router = Router()
load_dotenv()

admin = os.getenv("ADMIN_ID")

@set_router.message(I18nTextFilter("Settings"))
async def select_setting(message: Message, state: FSMContext):

    admin_msg = (
               f"User {message.from_user.first_name} purchased a subscription!"
            )

    await message.bot.send_message(
        chat_id=admin,

        text=admin_msg
    )

