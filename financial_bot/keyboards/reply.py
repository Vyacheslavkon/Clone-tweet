from aiogram.types import KeyboardButton
from aiogram.utils.i18n import gettext as _
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=_("Enter amount")),
        KeyboardButton(text=_("Add/change data")),
        KeyboardButton(text=_("Generate report")),
    )

    builder.row(KeyboardButton(text=_("Settings")), KeyboardButton(text="AI"))
    builder.row(KeyboardButton(text=_("cancel")))

    return builder.as_markup(resize_keyboard=True)


def change_data():
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=_("monthly planned budget")),
        KeyboardButton(text=_("limit expense")),
        KeyboardButton(text=_("savings goal")),
    )
    builder.row(KeyboardButton(text=_("cancel")))

    return builder.as_markup(resize_keyboard=True)
