from decimal import Decimal, InvalidOperation
from datetime import datetime, time, timezone, timedelta
import calendar

from aiogram.utils.i18n import gettext as _

from financial_bot.schemas import Plan


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


def fmt_limit_expense(expense: Decimal, plan: Plan):
     limit_expense = plan.monthly_budget / 100 * plan.budget_remind_percent
     balance_limit = limit_expense - expense
     diff_limit = limit_expense - balance_limit
     balance_limit_persent = round(diff_limit / limit_expense * 100)

     return  limit_expense, balance_limit_persent



def formatters(data: list, period_name: str, plan: Plan = None) -> str:

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

        if period_name != "day" and plan:
            def fmt(val):return f"{val:,.2f}".replace(",", " ")

            planning_lines = []


            if plan.monthly_budget:
                planning_lines.append(_(f"  • Planned budget: {fmt(plan.monthly_budget)} "))
            if plan.budget_remind_percent:
                lim_expense, balance = fmt_limit_expense(expense_total, plan)
                planning_lines.append(_(f"  • Limit expense: {fmt(lim_expense)}"))
                planning_lines.append(_(f"  • Limit spent: {balance}%"))
            if plan.savings_goal:
                planning_lines.append(_(f"  • Savings goal: {fmt(plan.savings_goal)} "))

            if planning_lines:
                report_text += "\n\n🎯 <b>Planning:</b>\n" + "\n".join(planning_lines)



    return report_text


def format_multi_report(reports_data: list[dict]) -> str:
    """
    Принимает список словарей вида:
    [{'data': data, 'period_name': '...', 'plan': plan}, ...]
    """
    parts = []
    for el in reports_data:
        # Вызываем ваш основной formatter для каждой части
        part = formatters(el['data'], el['period_name'], el.get('plan'))
        parts.append(part)

    # Склеиваем всё через красивый разделитель
    return "\n\n" + "───────────────────\n".join(parts)



def get_arbitrary_period(start_date, end_date):

    if end_date < start_date:
        start_date, end_date = end_date, start_date

    final_start = start_date.replace(hour=0, minute=0, second=0)
    final_end = end_date.replace(hour=23, minute=59, second=59)

    return final_start, final_end


def get_week_boundaries(name_week: str = None):
    now = datetime.now(timezone.utc)
    if name_week is None:
        target_date = now
    else:
        target_date = now - timedelta(days=7)

    start_of_week = target_date - timedelta(days=target_date.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

    end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)

    return start_of_week, end_of_week





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


