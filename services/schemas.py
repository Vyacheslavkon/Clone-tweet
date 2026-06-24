from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from decimal import Decimal


class ReceiptItemSchema(BaseModel):
    model_config = ConfigDict(extra='ignore')
    name: str = Field(description="Очищенное название товара или услуги (например, 'Молоко 3.2% 1л')")
    price: Decimal = Field(description="Финальная стоимость этой позиции с учетом скидок")
    #category: Optional[str] = Field(description="Категория этого конкретного товара (например, food, health, transport)")


class ReceiptAnalysisSchema(BaseModel):
    model_config = ConfigDict(extra='ignore')
    description: Optional[str] = Field(
        default=None,
        description="Название магазина, бренда или организации (например, 'ВкусВилл', 'Яндекс.Такси')")
    amount: Decimal = Field(description="Итоговая сумма всего чека")
    currency: str = Field(default="RUB", description="ISO код валюты (RUB, USD, EUR)")
    category: str = Field(default=None, description="Основная категория для всего чека (выбирается по наибольшим тратам)")
    items: List[ReceiptItemSchema] = Field(default=[], description="Список всех позиций в чеке")
    # is_shopping_related: bool = Field(
    #     description="True, если текст содержит информацию о покупках и ценах/суммах. False в противном случае."
    # )
    # error_message: str | None = Field(
    #     default=None,
    #     description="Если is_shopping_related=False или total_amount=0, напиши здесь короткий, ироничный или шутливый ответ пользователю на языке пользователя."
    # )

class ReceiptListAnalysisSchema(BaseModel):
    model_config = ConfigDict(extra='ignore')

    is_shopping_related: bool = Field(
        description="True, если текст содержит информацию о покупках и ценах/суммах. False в противном случае."
    )
    error_message: str | None = Field(
        default=None,
        description="Если is_shopping_related=False или total_amount=0, напиши здесь короткий, ироничный или шутливый ответ пользователю на языке пользователя."
    )
    transactions: List[ReceiptAnalysisSchema] = Field(default=[], description="Список транзакций, разделенных строго по категориям")