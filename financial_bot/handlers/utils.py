from decimal import Decimal, InvalidOperation
from datetime import datetime, time, timezone
import calendar

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


def formatters(data: list, period_name: str) -> str:

    if not data:
        report_text = _("There is no data for {period} 🤷‍♂️").format(period=period_name)
    else:
        income_total = 0
        expense_total = 0
        income_details = ""
        expense_details = ""

        for row in data:
            formated_amount = f"{row.total:,.2f}".replace(",", " ")
            if row.type == 'income':
                income_total += row.total
                income_details += f"  • {row.category}: {formated_amount}\n"
            else:
                expense_total += row.total
                expense_details += f"  • {row.category}: {formated_amount}\n"

        total_inc_str = f"{income_total:,.2f}".replace(",", " ")
        total_exp_str = f"{expense_total:,.2f}".replace(",", " ")

        report_text = _(
            "<b>Report for {period}:</b>\n\n"
            "💰 <b>Incomes: {total_inc_str}</b>\n{income_details}"
            f"\n"
            "💸 <b>Expense: {total_exp_str}</b>\n{expense_details}"
        ).format(
            period=period_name,
            total_inc_str=total_inc_str,
            total_exp_str=total_exp_str,
            income_details=income_details,
            expense_details=expense_details
        )

    return report_text


def get_month_boundaries():


    now = datetime.now(timezone.utc)

    start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    _, last_day = calendar.monthrange(now.year, now.month)

    end_month = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)
    current_month = now.month
    return start_month, end_month, current_month


def get_month_name(number: int) -> str:
    month_rus = [
        "",
        _("January"), _("February"), _("March"),
        _("April"), _("May"), _("June"),
        _("July"), _("August"), _("September"),
        _("October"), _("November"), _("December")
    ]

    return month_rus[number]