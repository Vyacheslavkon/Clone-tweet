from decimal import Decimal, InvalidOperation
from aiogram.utils.i18n import gettext as _

def check_value_budget(amount: str) -> Decimal | str:
    try:
        val = Decimal(amount.replace(',', '.').strip())
    except (InvalidOperation, ValueError):
        return "invalid_format"

    if val > 0:
        return val

    else:
        return "too_small"


def comparison(budget: Decimal, second_value: str) -> Decimal | None:
    try:
        val = Decimal(second_value.replace(',', '.').strip())
    except (InvalidOperation, ValueError):
        return "invalid_format"

    if budget is None or budget == 0:
        return "no_budget"

    if val > budget:
        return "too_big"

    if val <= 0:
        return "too_small"

    return val


def transform(budget: Decimal, second_value: str) -> Decimal | None:
    limit_expense = comparison(budget, second_value)

    if isinstance(limit_expense, str):
        return limit_expense


    lim_exp_pers = round(limit_expense / budget * 100)
    return lim_exp_pers



def get_error_text(error_code: str) -> str:
    errors = {
        "invalid_format": _("**Please enter a valid number.**\nFor example: 500 or 100.50"),
        "no_budget": _("**You don't have a budget set!**\nSet a basic budget first."),
        "too_big": _("**This amount exceeds your total budget.**"),
        "too_small": _("**The amount must be greater than zero.**"),
    }
    return errors.get(error_code, _("**An unexpected error occurred.**"))



