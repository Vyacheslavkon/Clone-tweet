import io
import os
from typing import Type, TypeVar

from dotenv import load_dotenv
from loguru import logger
from openai import AsyncOpenAI
from pydantic import BaseModel

from services.prompts import get_voice_message, get_analysis_financial


load_dotenv()

proxy_api_key = os.getenv("OPENAI_API_KEY")
if not proxy_api_key:
    raise ValueError(
        "Critical error: OPENAI_API_KEY must be set in the environment variables."
    )

proxy_base_url = os.getenv("OPENAI_BASE_URL")
if not proxy_base_url:
    raise ValueError(
        "Critical error: OPENAI_BASE_URL must be set in the environment variables."
    )


class AIService:
    T = TypeVar("T", bound=BaseModel)  # test

    def __init__(self, api_key: str, base_url: str, model: str = "gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=60.0)
        self.model = model

    async def analyze_image(
        self,
        image_url: str,
        # response_schema: Type[BaseModel],
        response_schema: Type[T],
        system_prompt: str,
        user_prompt: str = "Разбери этот чек по позициям согласно схеме.",
    ) -> T:

        completion = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                # Картинку и задачу отдаем в пользовательский промт
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ],
            response_format=response_schema,
            temperature=0.0,
        )
        parsed_result = completion.choices[0].message.parsed
        if parsed_result is None:
            raise ValueError("Failed to parse response")

        return parsed_result

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
        self, response_schema: Type[BaseModel], text: str, locale: str
    ):

        completion = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": get_voice_message(locale)},
                {"role": "user", "content": text},
            ],
            response_format=response_schema,
            max_completion_tokens=1024,
            temperature=0.0,
        )

        # Получаем валидированный Pydantic-объект
        return completion.choices[0].message.parsed

    async def process_voice_message(
        self,
        voice_bytes: bytes,
        locale: str,
        response_schema: Type[BaseModel],
    ):

        audio_file = io.BytesIO(voice_bytes)
        audio_file.name = "voice.ogg"

        transcript = await self.client.audio.transcriptions.create(
            model="whisper-1", file=audio_file
        )

        user_text = transcript.text
        logger.info("Recognized voice: {text}", text=user_text)

        return await self.process_receipt(
            text=user_text, response_schema=response_schema, locale=locale
        )


    async def analysis_financial(
            self,
            response_schema: Type[BaseModel],
            summary_data: dict,
            days: int,
            actual_days: int
    ) -> dict:

        if not summary_data:
            return {"error": "no_data"}


        categories_block = "\n".join([
            f"- {cat['category']}: {cat['amount']} руб. ({cat['count']} шт.)"
            for cat in summary_data.get("categories", [])
        ])


        items_block = "\n".join([
            f"- Дата: {item['date']} | {item['name']} | Цена: {item['total_amount']} руб. | Категория в БД: {item['category']}"
            for item in summary_data.get("top_items", [])
        ])


        config = summary_data.get("user_config", {})
        currency = config.get("currency", "руб.")

        config_lines = [f"- Валюта пользователя: {currency}"]
        if config.get("monthly_budget"):
            config_lines.append(f"- Месячный лимит расходов: {config['monthly_budget']} {currency}")
            config_lines.append(f"- Процент напоминания о бюджете: {config['budget_remind_percent']}%")
        if config.get("savings_goal"):
            config_lines.append(f"- Цель по сбережениям на месяц: {config['savings_goal']} {currency}")

        config_block = "\n".join(config_lines)


        user_context = f"""
           Период анализа: {summary_data['days_period']} дней.
           Всего получено доходов: {summary_data.get('total_income', 0.0)} {currency}.
           Всего потрачено расходов: {summary_data['total_amount']} {currency} (Используй это число как финальное и неизменное в поле общего итога).
           Чистый баланс за период (Доходы - Расходы): {summary_data.get('net_balance', 0.0)} {currency}.
           Количество расходных транзакций: {summary_data['total_count']}.

           === ФИНАНСОВЫЕ НАСТРОЙКИ И ЦЕЛИ ПОЛЬЗОВАТЕЛЯ ===
           {config_block}

           === РАСПРЕДЕЛЕНИЕ РАСХОДОВ ПО КАТЕГОРИЯМ В БД ===
           {categories_block}

           === ХРОНОЛОГИЧЕСКИЙ ПОТОК ПОКУПОК ИЗ ЧЕКОВ (СГРУППИРУЙ СЕМАНТИЧЕСКИ САМОСТОЯТЕЛЬНО) ===
           {items_block}

           В отчете используй только указанные выше цифры. Не округляй их и не пытайся пересчитать общую сумму расходов, доходов или баланса самостоятельно.
           В тексте отчета запрещено использовать любые HTML теги, кроме <b>, <i>, <code>. Использование тегов с атрибутами (например, class или style) строго табуировано.
           """

        completion = await self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": get_analysis_financial(days, actual_days)},
                {"role": "user", "content": user_context}
            ],
            response_format=response_schema,
            temperature=0.7
        )

        return completion.choices[0].message.parsed


ai_service = AIService(api_key=proxy_api_key, base_url=proxy_base_url)
