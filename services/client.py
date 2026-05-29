from openai import AsyncOpenAI
from pydantic import BaseModel
from typing import Type

class AIService:
    def __init__(self, api_key: str, base_url: str, model: str = "gpt-4o-mini"):
        # Инициализируем клиент, готовый работать с любым прокси-шлюзом
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def analyze_image(self, image_url: str, response_schema: Type[BaseModel], prompt: str) -> BaseModel:
        """Универсальный метод для распознавания чеков со строгой структурой ответа"""
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ],
                }
            ],
            response_format=response_schema,
        )
        return completion.choices.message.parsed


# Инициализируем сервис один раз при запуске воркера
# ai_service = AIService(
#     api_key=settings.AI_API_KEY,
#     base_url=settings.AI_BASE_URL, # Сюда передаем URL реселлера
#     model="gpt-4o-mini"
#)