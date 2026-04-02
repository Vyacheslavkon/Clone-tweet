from pydantic import BaseModel, ConfigDict
from decimal import Decimal


class CreateUser(BaseModel):

    tg_id: int

    language_code: str

    first_name: str

    model_config = ConfigDict(from_attributes=True)



class AddTransaction(BaseModel):

    amount: Decimal

    type: str

    category: str

    description: str

    model_config = ConfigDict(from_attributes=True)


