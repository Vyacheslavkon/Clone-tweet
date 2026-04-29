from decimal import Decimal, InvalidOperation

from aiogram.utils.i18n import gettext as _


def check_value_budget(amount: str) -> Decimal | str:
    try:
        val = Decimal(amount.replace(",", ".").strip())
    except (InvalidOperation, ValueError):
        return "invalid_format"

    if val > 0:
        return val

    else:
        return "too_small"


def comparison(budget: Decimal, second_value: str) -> Decimal | str:
    try:
        val = Decimal(second_value.replace(",", ".").strip())
    except (InvalidOperation, ValueError):
        return "invalid_format"

    if budget is None or budget == 0:
        return "no_budget"

    if val > budget:
        return "too_big"

    if val <= 0:
        return "too_small"

    return val


def transform(budget: Decimal, second_value: str) -> int | str:
    limit_expense = comparison(budget, second_value)

    if isinstance(limit_expense, str):
        return limit_expense

    return round(limit_expense / budget * 100)


def get_error_text(error_code: str) -> str:
    errors = {
        "invalid_format": _("Please enter a valid number."),
        "no_budget": _("You don't have a monthly planned budget set! Set a basic monthly planned budget first."),
        "too_big": _("This amount exceeds your planned budget."),
        "too_small": _("The amount must be greater than zero."),
    }
    return errors.get(error_code, _("An unexpected error occurred."))
