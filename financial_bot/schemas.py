from pydantic import BaseModel, ConfigDict

class CreateUser(BaseModel):

    tg_id: int

    language_code: str

    first_name: str

    model_config = ConfigDict(from_attributes=True)