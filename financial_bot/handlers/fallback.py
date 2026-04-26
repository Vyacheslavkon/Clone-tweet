from aiogram import Router
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

from financial_bot.keyboards.reply import get_main_menu

router_fallback = Router()


@router_fallback.message()
async def any_unhandled_event(message: Message):
    await message.reply(
        _("Sorry, I didn't understand you, please use the suggested choice!"),
        reply_markup=get_main_menu(),
    )
