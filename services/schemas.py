from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReceiptItemSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(
        description="Очищенное название товара или услуги (например, 'Молоко 3.2% 1л')"
    )
    price: Decimal = Field(
        description="Финальная стоимость этой позиции с учетом скидок"
    )
    # category: Optional[str] = Field(description="Категория этого конкретного товара (например, food, health, transport)")


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class ExpenseCategory(str, Enum):
    FOOD = "food"
    TRANSPORT = "transport"
    HOME = "home"
    ENTERTAINMENT = "entertainment"
    HEALTH = "health"
    OTHER = "other"


class IncomeCategory(str, Enum):
    SALARY = "salary"
    BONUS = "bonus"
    GIFT = "gift"
    DEAL = "deal"
    OTHER = "other"


class ReceiptAnalysisSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    description: Optional[str] = Field(
        default=None,
        description="Название магазина, бренда или организации (например, 'ВкусВилл', 'Яндекс.Такси')",
    )
    amount: Decimal = Field(description="Итоговая сумма всего чека")
    category: str = Field(
        description="Категория транзакции. Для expense строго из списка расходов, для income — из списка доходов."
    )  # delete default=None
    items: List[ReceiptItemSchema] = Field(
        default=[],
        description="Список позиций. Для обобщенных сценариев или доходов содержит ровно один элемент.",
    )
    type: TransactionType = Field(
        description="Тип транзакции: 'income' для доходов, 'expense' для расходов"
    )

    @model_validator(mode="before")
    @classmethod
    def fix_and_validate_categories(cls, data: dict) -> dict:

        if not isinstance(data, dict):
            return data

        valid_expenses = {
            "food",
            "transport",
            "home",
            "entertainment",
            "health",
            "other",
        }
        valid_income = {"salary", "bonus", "gift", "deal", "other"}

        category = data.get("category")
        tx_type = data.get("type")

        if not data.get("description"):
            data["description"] = "income" if tx_type == "income" else "expense"

        if isinstance(category, str):
            cleaned_category = category.strip().lower()

            if tx_type == "income":
                if cleaned_category not in valid_income:
                    cleaned_category = "other"
            elif tx_type == "expense":
                if cleaned_category not in valid_expenses:
                    cleaned_category = "other"
            else:

                cleaned_category = "other"

            data["category"] = cleaned_category

        return data


class ReceiptListAnalysisSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    is_shopping_related: bool = Field(
        description="True, если в тексте есть хотя бы одна валидная финансовая операция (доход или расход) с ценой. False во всех остальных случаях."
    )
    error_message: str | None = Field(
        default=None,
        description="Если is_shopping_related=False или amount=0, напиши здесь короткий, ироничный или шутливый ответ пользователю на языке пользователя.",
    )
    transactions: List[ReceiptAnalysisSchema] = Field(
        default=[], description="Список транзакций, разделенных строго по категориям"
    )


# class AnalyzedItem(BaseModel):
#     name: str = Field(description="Название товара из чека")
#     original_category: str = Field(description="Категория из БД бота (food, home, health и т.д.)")
#     expense_type: str = Field(
#         description="Строго один из вариантов: 'essential' (жизненно важно: лекарства, аренда, базовые продукты) или 'discretionary' (необязательно: рестораны, такси комфорт, развлечения, подписки)"
#     )
#
# class TargetRecommendation(BaseModel):
#     target_item_or_category: str = Field(description="Название конкретного товара или категории для оптимизации")
#     reason: str = Field(description="Аргументированный совет, почему и как можно оптимизировать (без банальностей)")
#     #potential_saving: float = Field(description="Сколько примерно можно сэкономить, если оптимизировать этот пункт")
#     potential_saving: str = Field(
#         description="Оценка потенциала экономии в свободной форме (например: 'Около 1500 руб в месяц, если сократить частоту до 2 раз в неделю' или 'До 20% от текущих трат на эту позицию')")
#
# class AIAnalysisResponse(BaseModel):
#     #summary: str = Field(description="Общий анализ финансового поведения за период (до 3 предложений)")
#     summary: str = Field(
#         description="Глубокий аудит финансового поведения за указанный период (до 4 предложений). "
#                     "ВАЖНО: Если ты упоминаешь общую сумму расходов, ты обязан продублировать её "
#                     "строго в том виде, в котором она передана в 'user_context', без округлений!"
#     )
#     classified_items: List[AnalyzedItem] = Field(description="Классификация топ-товаров пользователя по типу важности")
#     recommendations: List[TargetRecommendation] = Field(description="Список из 2-3 точечных советов ПО ГИБКИМ РАСХОДАМ")



class AnalyzedItem(BaseModel):
    name: str = Field(description="Название товара из чека")
    original_category: str = Field(description="Категория из БД бота (food, home, health и т.д.)")
    expense_type: str = Field(
        description="Строго один из вариантов: 'essential' (жизненно важно: лекарства, аренда, базовые продукты) или 'discretionary' (необязательно: рестораны, такси комфорт, развлечения, подписки)"
    )


class TargetRecommendation(BaseModel):
    target_item: str = Field(description="Название конкретного товара, услуги или привычки (из поля 'name' в 'top_items'), которая оптимизируется")
    reason: str = Field(description="Аргументированный совет, почему и как можно оптимизировать (без банальностей)")
    potential_saving: str = Field(
        description="Оценка потенциала экономии в свободной форме (например: 'Около 1000 руб в неделю, если...' или 'До 30% от трат на эту позицию')")


class AIAnalysisResponse(BaseModel):
    summary: str = Field(
        description="Глубокий аудит финансового поведения за указанный период (до 4 предложений). "
                    "Включи сюда оценку общего баланса (соотношение доходов и расходов). "
                    "ВАЖНО: Если ты упоминаешь общие суммы расходов, доходов или баланса, ты обязан продублировать их "
                    "строго в том виде, в котором они переданы в 'user_context', без округлений!"
    )


    budget_status: str = Field(
        description="Короткий вердикт по бюджету и целям сбережений. Примеры: 'Идеально укладываетесь в лимит', 'Лимит превышен', 'Цель по сбережениям под угрозой', 'Бюджет не задан'"
    )
    budget_usage_percent: Optional[float] = Field(
        default=None,
        description="Процент израсходованного месячного бюджета. Рассчитай на основе переданного лимита. Если лимит не задан в 'user_context', верни null."

    )

    classified_items: List[AnalyzedItem] = Field(description="Классификация топ-товаров пользователя по типу важности")
    recommendations: List[TargetRecommendation] = Field(description="Список из 2-3 точечных советов ПО ГИБКИМ РАСХОДАМ")


class WeeklyAnalysisResponse(BaseModel):
    summary: str = Field(
        description="Краткий оперативный аудит финансового поведения за прошедшую неделю (до 4 предложений). "
                    "Оцени общий баланс недели ('net_balance') относительно доходов. "
                    "Укажи, удается ли пользователю держать баланс в плюсе. "
                    "ВАЖНО: Копируй числовые агрегаты строго из 'user_context' без изменений и округлений!"
    )

    weekly_balance_status: str = Field(
        description="Короткий вердикт на текущий момент недели. Примеры: 'Расходы превысили доходы', 'Дисциплина на высоте! 🔥'"
    )
    classified_items: List[AnalyzedItem] = Field(description="Классификация топ-товаров пользователя за неделю по типу важности")
    recommendations: List[TargetRecommendation] = Field(description="Список из 2-3 точечных советов СТРОГО по конкретным позициям трат (labels)")



class MonthlyAnalysisResponse(BaseModel):
    summary: str = Field(
        description="Глубокий стратегический аудит финансового поведения за месяц (до 4 предложений). "
                    "Оцени структуру трат, накопительный эффект привычек и общий чистый баланс. "
                    "ВАЖНО: Копируй числовые агрегаты строго из 'user_context' без изменений и округлений!"
    )
    budget_status: str = Field(
        description="Вердикт по месячному бюджету и целям сбережений. Примеры: 'Идеально укладываетесь в лимит', 'Лимит превышен', 'Цель по сбережениям под угрозой', 'Бюджет не задан'"
    )
    budget_usage_percent: Optional[float] = Field(
        default=None,
        description="Процент израсходованного месячного лимита 'monthly_budget'. Рассчитай на основе переданного лимита. Если лимит не задан, верни null."
    )
    classified_items: List[AnalyzedItem] = Field(description="Классификация топ-товаров пользователя по типу важности за месяц")
    recommendations: List[TargetRecommendation] = Field(description="Список из 2-3 советов по оптимизации месячных системных привычек")