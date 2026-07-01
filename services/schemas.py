from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional, List
from decimal import Decimal
from enum import Enum

class ReceiptItemSchema(BaseModel):
    model_config = ConfigDict(extra='ignore')
    name: str = Field(description="Очищенное название товара или услуги (например, 'Молоко 3.2% 1л')")
    price: Decimal = Field(description="Финальная стоимость этой позиции с учетом скидок")
    #category: Optional[str] = Field(description="Категория этого конкретного товара (например, food, health, transport)")


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
    model_config = ConfigDict(extra='ignore')
    description: Optional[str] = Field(
        default=None,
        description="Название магазина, бренда или организации (например, 'ВкусВилл', 'Яндекс.Такси')")
    amount: Decimal = Field(description="Итоговая сумма всего чека")
    category: str = Field(description="Категория транзакции. Для expense строго из списка расходов, для income — из списка доходов.")# delete default=None
    items: List[ReceiptItemSchema] = Field(default=[], description="Список позиций. Для обобщенных сценариев или доходов содержит ровно один элемент.",)
    type: TransactionType = Field(
        description="Тип транзакции: 'income' для доходов, 'expense' для расходов"
    )

    @model_validator(mode='before')
    @classmethod
    def fix_and_validate_categories(cls, data: dict) -> dict:

        if not isinstance(data, dict):
            return data

        valid_expenses = {"food", "transport", "home", "entertainment", "health", "other"}
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
    model_config = ConfigDict(extra='ignore')

    is_shopping_related: bool = Field(
        description="True, если в тексте есть хотя бы одна валидная финансовая операция (доход или расход) с ценой. False во всех остальных случаях."
    )
    error_message: str | None = Field(
        default=None,
        description="Если is_shopping_related=False или amount=0, напиши здесь короткий, ироничный или шутливый ответ пользователю на языке пользователя."
    )
    transactions: List[ReceiptAnalysisSchema] = Field(default=[], description="Список транзакций, разделенных строго по категориям")