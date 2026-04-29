from aiogram.types import InlineKeyboardButton
from aiogram.utils.i18n import gettext as _
from aiogram.utils.keyboard import InlineKeyboardBuilder


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


def get_category(type_transaction: str):

    if type_transaction == "income":
        categories = [_("Salary"), _("Bonus"), _("Gift"), _("Deal"), _("Other")]
    else:
        categories = [
            _("Food"),
            _("Home"),
            _("Entertainment"),
            _("Transport"),
            _("Health"),
            _("Other"),
        ]
    builder = InlineKeyboardBuilder()

    for cat in categories:
        builder.add(
            InlineKeyboardButton(text=_(cat), callback_data=f"cat_{cat.lower()}")
        )
    builder.adjust(2)

    back_builder = get_back_kb()
    cancel_builder = cancel()
    builder.attach(back_builder)
    builder.attach(cancel_builder)

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

    builder.add(
        InlineKeyboardButton(text="day", callback_data="day")
    )

    builder.add(
        InlineKeyboardButton(text="month", callback_data="month")
    )

    builder.adjust(2)
    cancel_builder = cancel()
    builder.attach(cancel_builder)

    return builder.as_markup()