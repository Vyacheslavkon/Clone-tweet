from pydantic import BaseModel, ConfigDict, Field, model_validator
from decimal import Decimal
from typing import Optional

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

    @model_validator(mode="after")
    def check_goal_less_than_budget(self) -> "AddData":
        # Проверяем, что оба значения установлены (не None)
        if self.savings_goal is not None and self.monthly_budget is not None:
            if self.savings_goal >= self.monthly_budget:
                raise ValueError("Цель накоплений должна быть меньше месячного бюджета")
        return self

