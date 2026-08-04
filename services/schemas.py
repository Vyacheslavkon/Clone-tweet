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


class AnalyzedItem(BaseModel):
    name: str = Field(description="Название товара из чека")
    original_category: str = Field(description="Категория из БД бота (food, home, health и т.д.)")
    expense_type: str = Field(

        description="Строго один из двух вариантов:\n"
                    "1. 'essential' (Жизненно важно: лекарства, базовая медицина, аренда, детские и школьные товары в том числе канцелярия, коммунальные услуги, ремонт критических поломок).\n"
                    "2. 'discretionary' (Гибкие траты: кофе на вынос, рестораны, такси повышенного класса, игры, подписки, хобби, декор, спонтанные покупки)."
    )


class TargetRecommendation(BaseModel):
    target_item: str = Field(description="Название конкретного товара, услуги или привычки (из поля 'name' в 'top_items'), которая оптимизируется")
    reason: str = Field(description="Аргументированный совет, почему и как можно оптимизировать (без банальностей)")
    potential_saving: str = Field(
        description="Оценка потенциала экономии в свободной форме (например: 'Около 1000 руб в неделю, если...' или 'До 30% от трат на эту позицию')")


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


class MonthlyAnalyzedCategory(BaseModel):
    name: str = Field(
        description="Название укрупненной группы расходов на языке пользователя. "
                    "ТЫ ОБЯЗАН СГРУППИРОВАТЬ похожие товары из сырых данных в один бакет! "
                    "ПРИМЕР КАК НАДО: Если в данных есть 'Зубная паста', 'Дезодорант', 'Капли для глаз', "
                    "ты ОБЯЗАН объединить их в ОДИН объект с name='Средства гигиены и аптека'. "
                    "Если есть 'Хлеб', 'Молоко', 'Колбаса' — объедини в name='Продукты питания'. "
                    "ПРИМЕР КАК НЕЛЬЗЯ: Создавать отдельные объекты для 'Зубная паста' и 'Дезодорант'. "
                    "Количество объектов в classified_items должно быть строго меньше, чем в сырых данных, "
                    "за счет умного объединения похожих трат."
    )
    frequency_metric: str = Field(
        description="Суммарная частота покупок ВСЕХ товаров, которые ты объединил в эту группу. "
                    "Если ты объединил зубную пасту (1 транзакция) и дезодорант (1 транзакция), "
                    "то частота этой группы будет: '2 транзакции за 4 дня' (или за месяц)."
    )
    original_category: str = Field(
        description="Строгий системный ключ категории из БД бота (food, home, health, entertainment, other)."
    )
    expense_type: str = Field(
        description="Строго один из двух вариантов: 'essential' или 'discretionary'"
    )




class MonthlyCategoryRecommendation(BaseModel):

    target_habit_pattern: str = Field(
        description="Назови выявленный системный ритуал или повторяющуюся привычку пользователя "
                    "на основе частоты и количества транзакций за месяц. "
                    "Примеры: 'Регулярные перекусы и кофе на вынос', 'Частые мелкие покупки игрушек', "
                    "'Системные поездки на такси вместо общественного транспорта', 'Регулярный фастфуд'. "
                    "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать название одной конкретной покупки (например, 'Игрушка автобус'). "
                    "Название должно описывать именно повторяющийся паттерн поведения во множественном числе."
    )

    frequency_metric: str = Field(
        description="Укажи частоту этого ритуала за месяц, которую ты насчитал в сырых данных. "
                    "Пример: 'Куплено 14 раз за месяц', '7 поездок за 3 недели', 'Почти каждый день'."
    )

    reason: str = Field(
        description="Проанализируй эту привычку или группу трат в разрезе месяца. "
                    "Объясни пользователю, как этот паттерн влияет на его бюджет в долгосрочной перспективе. "
                    "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО упоминать конкретные имена, бренды или единичные события из сырых данных "
                    "(например, вместо 'Подарок Вике' пиши 'незапланированные расходы на подарки и праздники', "
                    "вместо 'Игрушка автобус' пиши 'спонтанные покупки для детей'). "
                    "Дай совет по контролю этой статьи расходов."
    )

    potential_saving: str = Field(
        description="Оценка потенциала экономии в рамках этого паттерна поведения за месяц (в свободной форме)."
    )


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
    classified_items: List[MonthlyAnalyzedCategory] = Field(
        description="Классификация ТОП-групп товаров пользователя по типу важности за месяц")
    recommendations: List[MonthlyCategoryRecommendation] = Field(
        description="Список из 2-3 советов по оптимизации месячных системных привычек")