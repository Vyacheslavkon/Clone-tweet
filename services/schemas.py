from decimal import Decimal
from enum import Enum
from typing import List, Optional, Literal

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



# class MonthlyAnalyzedCategory(BaseModel):
#
#     name: str = Field(
#         min_length=3,
#         description="The high-level category name generated strictly in the user's language (specified in system prompt). "
#         "FORBIDDEN: Do not use single product names (like 'Toothpaste', 'Milk') and do not copy raw database keys "
#         "as-is (like 'food', 'health', 'home', 'entertainment'). "
#         "You must translate and expand technical keys into proper generalized human-readable group names "
#         "in the target language (e.g., for Russian: 'food' -> 'Продукты', 'health' -> 'Лекарства и аптека')."
#     )
#
#
#     frequency_metric: str = Field(
#         description="The aggregated analytical frequency indicator for the entire created group over the month. "
#                     "Strict format required: 'X transactions per month' or 'Regularly (X times a week)', "
#                     "translated into the user's language specified in the system prompt. "
#                     "You must sum the count of all individual transactions that fall into this specific bucket."
#     )
#
#     expense_type: Literal["essential", "discretionary"] = Field(
#         description="Strictly classify the entire group into one of two options:\n"
#                     "1. 'essential' (Vital: standard groceries, supermarkets, medication, healthcare, housing, utilities, critical repairs).\n"
#                     "2. 'discretionary' (Flexible/Lifestyle: coffee to go, cafes, restaurants, bars, entertainment, hobbies, cinema, spontaneous shopping)."
#     )

class MonthlyAnalyzedCategory(BaseModel):
    name: str = Field(
        min_length=3,
        description=(
            "The high-level category name generated strictly in the user's language. "
            "INSTRUCTION: Scan the 'name' and 'category' fields in the raw data. "
            "If you see specific product tokens (like 'Toothpaste', 'T-shirt'), cluster them into narrow, "
            "accurate sub-categories (e.g., 'Hygiene & Cosmetics', 'Clothing & Shopping'). "
            "If you see only broad category tokens (like 'food', 'transport'), expand them into beautiful "
            "human-readable names (e.g., 'Groceries & Supermarkets', 'Transport & Auto'). "
            "Never use raw single product names as titles. Aim for a detailed layout."
        )
    )

    frequency_metric: str = Field(
        description="The aggregated indicator: 'X transactions per month' or 'Regularly (X times a week)' in the user's language."
    )
    expense_type: Literal["essential", "discretionary"] = Field(
        description="Strictly classify this specific category into 'essential' or 'discretionary' based on its current context."
    )

    items_breakdown: List[str] = Field(
        description="A list of specific transaction names or item descriptors from 'top_items' that formed this category. "
                    "For example, if name is 'Cafes & Fastfood', this list must contain items like ['McDonalds', 'KFC', 'Coffee']. "
                    "If the category was formed by manual entries without details, put the base category name here: ['Manual Entry Expenses']."
    )



class MonthlyCategoryRecommendation(BaseModel):
    target_habit_pattern: str = Field(
        description="The identified systemic behavioral ritual or recurring user spending habit based on transaction frequency over the month. "
                    "Examples formatted strictly in the user's language: 'Frequent snacks and coffee to go', 'Regular fast food purchases'. "
                    "FORBIDDEN: Never write the name of a specific single purchase (e.g., do NOT write 'Toy bus'). "
                    "The title MUST describe a recurring behavioral pattern in the plural form."
    )

    frequency_metric: str = Field(
        description="The exact frequency of this specific ritual counted across the raw monthly data. "
                    "Examples formatted strictly in the user's language: 'Purchased 14 times this month', '7 rides in 3 weeks', 'Nearly every day'."
    )

    reason: str = Field(
        description="A deep macro-analysis of this specific habit over the month. Explain to the user how this pattern "
                    "compounds and affects their long-term budget in the future. "
                    "STRICTLY FORBIDDEN: Do not mention specific personal names, brands, or unique single events from the raw data "
                    "(e.g., instead of 'Gift for Victoria' write 'unplanned expenses on gifts and holidays'; "
                    "instead of 'Toy bus' write 'spontaneous purchases for children'). "
                    "Provide actionable financial advice on how to control and track this expense category. Written strictly in the user's language."
    )

    potential_saving: str = Field(
        description="An estimate of the monthly savings potential within this behavioral pattern. "
                    "Format as a free-form encouraging text in the user's language (e.g., 'Up to 3,000 RUB per month if...')."
    )



class MonthlyAnalysisResponse(BaseModel):
    # summary: str = Field(
    #     description="A deep, strategic audit of the user's monthly financial behavior (maximum 4 sentences). "
    #                 "Evaluate the overall spending structure, the compounding effect of habits, and the net financial balance. "
    #                 "CRITICAL AGGREGATE RULE: You must copy all numerical aggregates strictly from the provided 'user_context' "
    #                 "without any modifications, calculations, or roundings! Written strictly in the user's language."
    # )
    summary: str = Field(
        description="A deep, strategic verbal audit of the user's monthly financial behavior (max 4 sentences). "
                    "CRITICAL: You are STRICTLY FORBIDDEN from generating or writing any percentage values (do NOT use the '%' symbol at all) "
                    "or calculating new balance numbers. Focus entirely on behavioral trends, lifestyle coaching, "
                    "and conceptual budget evaluation using ONLY the raw numbers passed in the context. "
                    "Written strictly in the user's language."
    )

    budget_status: str = Field(
        description="The final verdict on the monthly budget status and savings targets. "
                    "Examples formatted strictly in the user's language: 'Perfectly within limits', 'Limit exceeded', "
                    "'Savings goal at risk', 'Budget not set'."
    )
    budget_usage_percent: Optional[float] = Field(
        default=None,
        description="The calculated percentage of the consumed 'monthly_budget'. Calculate this value mathematically "
                    "based on the passed limit. If the monthly budget limit is not provided, strictly return null."
    )

    # ПРИМЕНЯЕМ ВАРИАНТ 1 (ИНВЕРСИЯ ПОЛЕЙ): рекомендации идут ПЕРВЫМИ для удержания фокуса внимания ИИ
    recommendations: List[MonthlyCategoryRecommendation] = Field(
        description="A list of 2-3 expert strategic optimization recommendations regarding systemic habits and behavioral rituals."
    )


    # classified_items: List[MonthlyAnalyzedCategory] = Field(
    #     description="A detailed classification of ALL expense groups for the month. "
    #                 "CRITICAL: You must generate between 6 and 10 distinct high-level category groups "
    #                 "to provide a comprehensive statistics block (e.g., separate 'Transport/Taxi', "
    #                 "'Subscriptions', 'Clothes & Shopping', 'Cafes & Fastfood' instead of merging everything into 'Other'). "
    #                 "Sort by volume from highest to lowest."
    # )

    classified_items: List[MonthlyAnalyzedCategory] = Field(
        description="A complete classification of all expense categories present in the user's data for the month, "
                    "sorted by total spending volume from highest to lowest."
    )




class AnalyzedItem(BaseModel):
    name: str = Field(description="Название конкретного товара из чека (например, 'Зубная паста') "
                     "ИЛИ название категории расходов, если детализация по товарам отсутствует (например, 'Транспорт', 'Продукты').")

    #original_category: str = Field(description="Категория из БД бота (food, home, health и т.д.)")
    expense_type: str = Field(

        description="Строго один из двух вариантов:\n"
                    "1. 'essential' (Жизненно важно: лекарства, базовая медицина, аренда, детские и школьные товары в том числе канцелярия, коммунальные услуги, ремонт критических поломок).\n"
                    "2. 'discretionary' (Гибкие траты: кофе на вынос, рестораны, такси повышенного класса, игры, подписки, хобби, декор, спонтанные покупки)."
    )

    frequency_metric: str = Field(
        description=" Показатель частоты транзакций для каждого товара или категории расходов за прошедшие дни недели. "
                    "Формат строго: 'Х транзакций за прошедшие дни недели'."

    )



class TargetRecommendation(BaseModel):
    # name: str = Field(
    #     description="Название конкретного товара из чека (например, 'Зубная паста') "
    #                 "ИЛИ название категории расходов, если детализация по товарам отсутствует (например, 'Транспорт', 'Продукты')."
    # )
    # expense_type: str = Field(
    #     description="Строго один из двух вариантов:\n"
    #                 "1. 'essential' (Жизненно важно: лекарства, коммунальные услуги, базовые продукты).\n"
    #                 "2. 'discretionary' (Гибкие траты: кофе, рестораны, развлечения)."
    # )
    target_item: str = Field(
        description="Название конкретного товара, услуги, привычки или категории расходов (из поля 'name' в 'top_items'), которая оптимизируется"
    )
    reason: str = Field(
        description="Аргументированный совет, почему и как можно оптимизировать расходы на этот товар или категорию."
    )
    potential_saving: str = Field(
        description="Оценка потенциала экономии в свободной форме."
    )



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

    classified_items: List[AnalyzedItem] = Field(
        description="Классификация топ-товаров пользователя за неделю по типу важности")

    recommendations: List[TargetRecommendation] = Field(description="Список из 2-3 точечных советов СТРОГО по конкретным позициям трат (labels)")