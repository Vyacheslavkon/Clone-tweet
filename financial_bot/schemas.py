from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateUser(BaseModel):

    tg_id: int

    language_code: str

    first_name: str

    model_config = ConfigDict(from_attributes=True)


class AddTransaction(BaseModel):

    user_id: int

    amount: Decimal

    type: str

    category: str

    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AddData(BaseModel):

    savings_goal: Optional[Decimal] = None

    monthly_budget: Optional[Decimal] = None

    budget_remind_percent: Optional[int] = Field(default=None, ge=1, le=99)

    model_config = ConfigDict(from_attributes=True)
