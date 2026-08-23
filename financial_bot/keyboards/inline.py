from typing import Callable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _
from aiogram.utils.keyboard import InlineKeyboardBuilder

from financial_bot.filters import DeleteTransactionCallback


def cancel():
    builder = InlineKeyboardBuilder()
    builder.button(text=_("Cancel"), callback_data="cancel")
    return builder


def get_back_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text=_("Back"), callback_data="back")
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


# def get_category(type_transaction: str):
#
#     if type_transaction == "income":
#         categories = [_("Salary"), _("Bonus"), _("Gift"), _("Deal"), _("Other")]
#     else:
#         categories = [
#             _("Food"),
#             _("Home"),
#             _("Entertainment"),
#             _("Transport"),
#             _("Health"),
#             _("Other"),
#         ]
#     builder = InlineKeyboardBuilder()
#
#     for cat in categories:
#         builder.add(
#             InlineKeyboardButton(text=_(cat), callback_data=f"cat_{cat.lower()}")
#         )
#     builder.adjust(2)
#
#     back_builder = get_back_kb()
#     cancel_builder = cancel()
#     builder.attach(back_builder)
#     builder.attach(cancel_builder)
#
#     return builder.as_markup()


def get_category(type_transaction: str):

    if type_transaction == "income":
        categories = {
            "salary": _("Salary"),
            "bonus": _("Bonus"),
            "gift": _("Gift"),
            "deal": _("Deal"),
            "other": _("Other"),
        }
    else:
        categories = {
            "food": _("Food"),
            "home": _("Home"),
            "entertainment": _("Entertainment"),
            "transport": _("Transport"),
            "health": _("Health"),
            "other": _("Other"),
        }

    builder = InlineKeyboardBuilder()

    for slug, label in categories.items():
        builder.add(InlineKeyboardButton(text=label, callback_data=f"cat_{slug}"))

    builder.adjust(2)
    builder.attach(get_back_kb())
    builder.attach(cancel())

    return builder.as_markup()


def get_description():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text=_("Skip description"), callback_data="skip_description"
        )
    )
    builder.adjust(2)

    back_builder = get_back_kb()
    cancel_builder = cancel()

    builder.attach(back_builder)
    builder.attach(cancel_builder)
    return builder.as_markup()


def period_report():
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(text=_("day"), callback_data="day"))

    builder.add(InlineKeyboardButton(text=_("week"), callback_data="week"))

    builder.add(InlineKeyboardButton(text=_("month"), callback_data="month"))

    builder.adjust(1)
    cancel_builder = cancel()
    builder.attach(cancel_builder)

    return builder.as_markup()


def report_history():

    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text=_("last two weeks"), callback_data="two_week")
    )

    builder.add(
        InlineKeyboardButton(text=_("arbitrary period"), callback_data="period")
    )

    builder.adjust(2)
    cancel_builder = cancel()
    builder.attach(cancel_builder)

    return builder.as_markup()


def get_delete_keyboard(batch_id: str, button_text: str):
    builder = InlineKeyboardBuilder()
    builder.button(
        text=button_text, callback_data=DeleteTransactionCallback(batch_id=batch_id)
    )
    return builder.as_markup()


def get_detailed_report(days: int, _: Callable[[str], str]):
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(text=_("🔎 Detailed report"), callback_data=f"show_detailed_report:{days}")
    )
    return builder.as_markup()




