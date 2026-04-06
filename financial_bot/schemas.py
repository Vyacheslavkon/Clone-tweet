from pydantic import BaseModel, ConfigDict
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


