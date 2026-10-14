from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.i18n import gettext as _
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=_("Enter amount")),
        KeyboardButton(text=_("Delete today's data")),
    )
    builder.row(
        KeyboardButton(text=_("Generate report")), KeyboardButton(text=_("History"))
    )

    builder.row(KeyboardButton(text=_("Add/change data")), KeyboardButton(text="AI"))

    builder.row(KeyboardButton(text=_("cancel")), KeyboardButton(text=_("Settings")))

    return builder.as_markup(resize_keyboard=True)


def change_data() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=_("monthly planned budget")),
        KeyboardButton(text=_("limit expense")),
        KeyboardButton(text=_("savings goal")),
    )
    builder.row(KeyboardButton(text=_("cancel")))

    return builder.as_markup(resize_keyboard=True)


def request_ai() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=_("weekly data analysis")),
        KeyboardButton(text=_("monthly data analysis")),
    )
    builder.row(KeyboardButton(text=_("data entry")))

    builder.row(KeyboardButton(text=_("cancel")))

    return builder.as_markup(resize_keyboard=True)


def settings() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=_("Change timezone")),
        KeyboardButton(text=_("Change language")),
        KeyboardButton(text=_("Change currency")),
    )

    builder.row(KeyboardButton(text=_("cancel")))

    return builder.as_markup(resize_keyboard=True)
