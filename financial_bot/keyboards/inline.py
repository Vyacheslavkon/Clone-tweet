from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.i18n import gettext as _

def cancel():
    builder  = InlineKeyboardBuilder()
    builder.button(text=_("Cancel"), callback_data="cancel")
    return builder


def get_back_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text=_("⬅️ Back"), callback_data="back")
    return builder


def get_type():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=_("Income"), callback_data="type_income"))
    builder.add(InlineKeyboardButton(text=_("Expense"), callback_data="type_expense"))
    builder.adjust(2)

    back_builder = get_back_kb()
    cancel_builder = cancel()

    builder.attach(back_builder)
    builder.attach(cancel_builder)
    return builder.as_markup()


def get_category():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=_("Food"), callback_data="cat_food"))
    builder.add(InlineKeyboardButton(text=_("Home"), callback_data="cat_home"))
    builder.add(InlineKeyboardButton(text=_("Entertainment"), callback_data="cat_entertainment"))
    builder.add(InlineKeyboardButton(text=_("Transport"), callback_data="cat_transport"))
    builder.add(InlineKeyboardButton(text=_("Health"), callback_data="cat_health"))
    builder.add(InlineKeyboardButton(text=_("Other"), callback_data="cat_other"))
    builder.adjust(2)

    back_builder = get_back_kb()
    cancel_builder = cancel()
    builder.attach(back_builder)
    builder.attach(cancel_builder)

    return builder.as_markup()


def get_description():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=_("Description"), callback_data="description"))
    builder.add(InlineKeyboardButton(text=_("Skip description"), callback_data="skip_description"))
    builder.adjust(2)

    back_builder = get_back_kb()
    cancel_builder = cancel()

    builder.attach(back_builder)
    builder.attach(cancel_builder)
    return builder.as_markup()
