import os
import io
from typing import Type
from pydantic import BaseModel
from openai import AsyncOpenAI
from dotenv import load_dotenv
from loguru import logger

from services.prompts import  get_system_prompt, get_voice_message

load_dotenv()

proxy_api_key = os.getenv("OPENAI_API_KEY")
proxy_base_url = os.getenv("OPENAI_BASE_URL")

class AIService:
    def __init__(self, api_key: str, base_url: str, model: str = "gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=60.0 )
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


    """for check"""
    # async def process_receipt(
    #         self,
    #         response_schema: Type[BaseModel],
    #         text: dict,
    #         locale: str
    # ):
    #
    #     completion = await self.client.beta.chat.completions.parse(
    #         model=self.model,
    #         messages=[
    #             {
    #                 "role": "system",
    #                 "content": get_system_prompt(locale)
    #             },
    #             {
    #                 "role": "user",
    #                 "content": text
    #             }
    #         ],
    #         response_format= response_schema,
    #         temperature=0.0
    #     )
    #
    #     # Получаем валидированный Pydantic-объект
    #     return completion.choices[0].message.parsed

    async def process_receipt(
            self,
            response_schema: Type[BaseModel],
            text: str,
            locale: str
    ):

        completion = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": get_voice_message(locale)
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            response_format= response_schema,
            temperature=0.0
        )

        # Получаем валидированный Pydantic-объект
        return completion.choices[0].message.parsed


    async def process_voice_message(
            self,
            voice_bytes: bytes,
            locale: str,
            response_schema: Type[BaseModel],):

        # 1. Оборачиваем байты в файлоподобный объект и задаем имя с правильным расширением
        audio_file = io.BytesIO(voice_bytes)
        audio_file.name = "voice.ogg"  # Чтобы OpenAI понял формат

        # 2. Мгновенно переводим голос в текст через Whisper
        transcript = await self.client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )

        user_text = transcript.text
        logger.info(f"Распознанный голос: {user_text}")


        # 3. Отправляем текст в gpt-4o-mini для структурирования
        # Используем вашу ГОТОВУЮ ReceiptAnalysisSchema!
        analysis_result = await self.process_receipt(
            text=user_text,
            response_schema=response_schema,
            locale=locale
        )

        return analysis_result







ai_service = AIService(api_key=proxy_api_key, base_url=proxy_base_url)








