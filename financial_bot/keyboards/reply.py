from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.utils.i18n import gettext as _

def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=_("Enter amount")),
                        KeyboardButton(text=_("Add data")),
                        KeyboardButton(text=_("Generate report"))
                )

    builder.row(KeyboardButton(text=_("Settings")), KeyboardButton(text="AI"))
    builder.row(KeyboardButton(text=_("cancel")))

    return builder.as_markup(resize_keyboard=True)
