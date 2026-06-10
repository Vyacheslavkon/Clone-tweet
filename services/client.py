import os
from typing import Type
from pydantic import BaseModel
from openai import AsyncOpenAI
from dotenv import load_dotenv

from services.prompts import PROMPT_FOR_TEXT

load_dotenv()

proxy_api_key = os.getenv("OPENAI_API_KEY")
proxy_base_url = os.getenv("OPENAI_BASE_URL")

class AIService:
    def __init__(self, api_key: str, base_url: str, model: str = "gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def analyze_image(
            self,
            image_url: str,
            response_schema: Type[BaseModel],
            system_prompt: str,
            user_prompt: str = "Разбери этот чек по позициям согласно схеме."
    ) -> BaseModel:

        completion = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                # Инструкции и правила отдаем в системный промт
                {
                    "role": "system",
                    "content": system_prompt
                },
                # Картинку и задачу отдаем в пользовательский промт
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ],
                }
            ],
            response_format=response_schema,
            temperature=0.0
        )
        return completion.choices[0].message.parsed


    async def process_receipt(
            self,
            response_schema: Type[BaseModel],
            text: dict
    ):
        """Отправляет структурированный текст в LLM и сохраняет в БД."""
        user_prompt: str = "Проанализируй текст распознанного чека."

        completion = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": PROMPT_FOR_TEXT
                },
                {
                    "role": "user",
                    "content": text  # Передаем обычную строку
                }
            ],
            response_format= response_schema,
        )

        # Получаем валидированный Pydantic-объект
        return completion.choices[0].message.parsed





ai_service = AIService(api_key=proxy_api_key, base_url=proxy_base_url)








