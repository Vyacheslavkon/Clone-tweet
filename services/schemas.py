from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal


class ReceiptItemSchema(BaseModel):
    name: str = Field(description="Очищенное название товара или услуги (например, 'Молоко 3.2% 1л')")
    price: Decimal = Field(description="Финальная стоимость этой позиции с учетом скидок")
    category: Optional[str] = Field(description="Категория этого конкретного товара (например, food, health, transport)")


class ReceiptAnalysisSchema(BaseModel):
    description: Optional[str] = Field(
        description="Название магазина, бренда или организации (например, 'ВкусВилл', 'Яндекс.Такси')")
    amount: Decimal = Field(description="Итоговая сумма всего чека")
    currency: str = Field(default="RUB", description="ISO код валюты (RUB, USD, EUR)")
    category: str = Field(description="Основная категория для всего чека (выбирается по наибольшим тратам)")
    items: List[ReceiptItemSchema] = Field(description="Список всех позиций в чеке")