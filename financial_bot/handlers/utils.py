from decimal import Decimal, InvalidOperation


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
        "invalid_format": "🔢 **Пожалуйста, введите корректное число.**\nНапример: 500 или 100.50",
        "no_budget": "📁 **У вас не установлен бюджет!**\nСначала задайте основной бюджет.",
        "too_big": "⚠️ **Эта сумма превышает ваш общий бюджет.**",
        "too_small": "❌ **Сумма должна быть больше нуля.**",
    }
    return errors.get(error_code, "🚫 **Произошла непредвиденная ошибка.**")



