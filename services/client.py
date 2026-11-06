import base64
import io
import json
import os
from dataclasses import dataclass
from typing import Awaitable, Callable, Type, TypeVar

import httpx
import openai
from loguru import logger
from openai import AsyncOpenAI
from pydantic import BaseModel

from core.config import STT_TIMEOUT, RECEIPT_MAX_TOKENS, ANALYSIS_MAX_TOKENS, CLIENT_TIMEOUT, CLIENT_MAX_RETRIES
from services.exceptions import is_failover_error, ProviderResponseError, TruncatedResponseError
from services.prompts import get_voice_message, language_name, get_analysis_financial

T = TypeVar("T", bound=BaseModel)

@dataclass(frozen=True)
class Backend:
    name: str
    client: AsyncOpenAI
    client_x: httpx.AsyncClient
    model: str
    stt_mode: str
    stt_model: str
    extra_body: dict | None = None



class AIService:
    def __init__(
        self,
        chat_backends: list[Backend],
        stt_backends: list[Backend],
        stt_model: str = "whisper-1",
    ):
        if not chat_backends:
            raise ValueError("AIService requires at least one chat backend")
        if not stt_backends:
            raise ValueError("AIService requires at least one STT backend")
        self.chat_backends = chat_backends
        self.stt_backends = stt_backends
        self.stt_model = stt_model


    @staticmethod
    async def _with_failover(

            backends: list[Backend],
            op: str,
            call: Callable[[Backend], Awaitable[T]],
    ) -> T:
        """Пробует провайдеров по очереди, пока кто-то не ответит.

        backends: упорядоченный список (первый основной, остальные резерв).
        op:       метка операции для логов ("receipt", "analysis", "stt").
        call:     корутина-функция, принимающая Backend и выполняющая запрос.
                  Запрос зависит от бэкенда (свой клиент, своё имя модели),
                  поэтому передаём функцию, а не готовый результат.

        Переключаемся только на ошибках доступности. Ошибки запроса
        (BadRequest, обрезка ответа, валидация) пробрасываются сразу:
        резерв их не исправит, а расход удвоится.
        """
        last: Exception | None = None
        for index, backend in enumerate(backends):
            try:
                result = await call(backend)
            except Exception as exc:  # noqa: PIE786
                if not is_failover_error(exc):
                    raise
                last = exc
                level = "error" if index == len(backends) - 1 else "warning"
                logger.log(
                    level.upper(),
                    "AI {op} failed on {name}: {err_type}: {err}",
                    op=op, name=backend.name, err_type=type(exc).__name__, err=exc,
                )
                continue
            if index > 0:
                logger.warning("AI {op} served by FALLBACK {name}", op=op, name=backend.name)
            else:
                logger.info("AI {op} served by {name}", op=op, name=backend.name)
            return result

        assert last is not None
        raise last


    async def _transcribe(self, voice_bytes: bytes) -> str:
        async def _call(b: Backend) -> str:

            model = b.stt_model
            if b.stt_mode == "multipart":
                audio = io.BytesIO(voice_bytes)
                audio.name = "voice.ogg"
                tr = await b.client.audio.transcriptions.create(
                    model=model, file=audio, timeout=STT_TIMEOUT
                )
                text = tr.text
            else:

                resp = await b.client_x.post(
                    "/audio/transcriptions",
                    json={
                        "model": b.stt_model,
                        "input_audio": {
                            "data": base64.b64encode(voice_bytes).decode("ascii"),
                            "format": "ogg",
                        },
                    },
                    timeout=STT_TIMEOUT,
                )

                resp.raise_for_status()
                text = resp.json().get("text", "")
            if not text:
                raise ProviderResponseError("Empty transcription from provider")
            return text

        return await self._with_failover(self.stt_backends, "stt", _call)


    async def process_voice_message(
            self, voice_bytes: bytes, locale: str, response_schema: Type[T]
    ) -> T:
        user_text = await self._transcribe(voice_bytes)
        logger.info("Recognized voice: {text}", text=user_text)
        return await self.process_receipt(
            text=user_text, response_schema=response_schema, locale=locale
        )

    async def process_receipt(
            self, response_schema: Type[T], text: str, locale: str
    ) -> T:
        schema_json = json.dumps(response_schema.model_json_schema())

        async def _call(b: Backend) -> str:
            completion = await b.client.chat.completions.create(
                model=b.model,
                messages=[
                    {"role": "system", "content": get_voice_message(locale)},
                    {
                        "role": "system",
                        "content": f"Return JSON strictly matching this schema: {schema_json}",
                    },
                    {"role": "user", "content": text},
                ],
                response_format={"type": "json_object"},
                max_completion_tokens=RECEIPT_MAX_TOKENS,
                temperature=0.0,
                extra_body=b.extra_body,
            )

            if not completion.choices:
                raise ProviderResponseError("Provider returned no choices")

            choice = completion.choices[0]
            if choice.finish_reason == "length":

                raise TruncatedResponseError(
                    "Response was truncated because it exceeded the token limit"
                )
            if not choice.message.content:
                raise ProviderResponseError("Provider returned empty content")
            return choice.message.content

        raw_json = await self._with_failover(self.chat_backends, "receipt", _call)
        return response_schema.model_validate_json(raw_json)

    @staticmethod
    def build_user_context(summary_data: dict, locale: str) -> str:
        config = summary_data.get("user_config", {})
        currency = config.get("currency") or "USD"  # код валюты, не "руб."

        categories_block = "\n".join(
            f"- {c['category']}: {c['amount']} {currency} ({c['count']} transactions)"
            for c in summary_data.get("categories", [])
        )
        items_block = "\n".join(
            f"- Date: {i['date']} | {i['name']} | Amount: {i['total_amount']} {currency} "
            f"| DB category: {i['category']}"
            for i in summary_data.get("top_items", [])
        )

        config_lines = [f"- User currency: {currency}"]
        if config.get("monthly_budget"):
            config_lines.append(
                f"- Monthly spending limit: {config['monthly_budget']} {currency}"
            )
            config_lines.append(
                f"- Budget reminder threshold: {config['budget_remind_percent']}%"
            )
        if config.get("savings_goal"):
            config_lines.append(
                f"- Monthly savings goal: {config['savings_goal']} {currency}"
            )

        return f"""
        Analysis period: {summary_data['days_period']} days.
        Total income: {summary_data.get('total_income', 0.0)} {currency}.
        Total expenses: {summary_data['total_amount']} {currency} (use this number as final and unchanged in the total field).
        Net balance (income - expenses): {summary_data.get('net_balance', 0.0)} {currency}.
        Number of expense transactions: {summary_data['total_count']}.

        === USER FINANCIAL SETTINGS AND GOALS ===
        {chr(10).join(config_lines)}

        === EXPENSES BY DB CATEGORY ===
        {categories_block}

        === CHRONOLOGICAL PURCHASES FROM RECEIPTS (GROUP SEMANTICALLY YOURSELF) ===
        {items_block}

        Use only the figures above. Do not round them or recompute totals.
        Only the HTML tags <b>, <i>, <code> are allowed, without attributes.

        RESPONSE LANGUAGE: write every free-text field strictly in {language_name(locale)}, even though
        item names above may be in another language. Translate common item names into
        {language_name(locale)}; keep brand names unchanged.
        """

    async def analysis_financial(
            self,
            response_schema: Type[T],
            summary_data: dict,
            days: int,
            actual_days: int,
            locale: str,
    ) -> T:
        if not summary_data:
            raise ValueError("analysis_financial requires non-empty summary_data")

        user_context = self.build_user_context(summary_data, locale)
        system_prompt = get_analysis_financial(days, actual_days, locale)

        async def _call(b: Backend) -> T:
            completion = await b.client.beta.chat.completions.parse(
                model=b.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_context},
                ],
                response_format=response_schema,
                max_completion_tokens=ANALYSIS_MAX_TOKENS,
                temperature=0.0,
                extra_body=b.extra_body,
            )
            if not completion.choices:
                raise ProviderResponseError("Provider returned no choices")

            message = completion.choices[0].message
            if message.refusal:

                logger.error("Model refused structured analysis: {r}", r=message.refusal)
                raise RuntimeError(f"Model refused response: {message.refusal}")
            if message.parsed is None:
                raise ProviderResponseError("Provider returned unparsable structured data")
            return message.parsed

        try:
            return await self._with_failover(self.chat_backends, "analysis", _call)
        except openai.LengthFinishReasonError as exc:
            logger.warning("Analysis truncated for schema {s}", s=response_schema.__name__)
            raise TruncatedResponseError("Analysis response was truncated") from exc


    async def close(self) -> None:
        unique = {id(b.client): b.client for b in (*self.chat_backends, *self.stt_backends)}
        for client in unique.values():
            await client.close()


def _make_backend(prefix: str, *, openrouter_extras: bool = False) -> Backend | None:
    api_key = os.environ.get(f"{prefix}_API_KEY")
    if not api_key:
        return None
    base_url = os.environ[f"{prefix}_BASE_URL"]
    name = os.environ.get(f"{prefix}_NAME", prefix.lower())
    stt_mode = os.environ[f"{prefix}_STT_MODE"]


    if stt_mode not in {"multipart", "base64_json"}:
        raise ValueError(f"{prefix}_STT_MODE must be 'multipart' or 'base64_json'")

    client_x = httpx.AsyncClient(
        base_url=base_url,
        headers={
            "Authorization": f"Bearer {api_key}",

            "Content-Type": "application/json"
        },

        timeout=httpx.Timeout(60.0, connect=10.0)
    )

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=CLIENT_TIMEOUT,
        max_retries=CLIENT_MAX_RETRIES,
        default_headers={"X-Title": "CapiMind"} if openrouter_extras else None,
    )
    return Backend(
        name=name,
        client_x=client_x,
        client=client,
        model=os.environ[f"{prefix}_MODEL"],
        extra_body={"provider": {"require_parameters": True}} if openrouter_extras else None,
        stt_mode=stt_mode,
        stt_model=os.environ[f"{prefix}_STT_MODEL"]

    )

def build_ai_service() -> AIService:
    primary = _make_backend("AI_PRIMARY", openrouter_extras="openrouter" in os.environ.get("AI_PRIMARY_BASE_URL", ""))
    fallback = _make_backend("AI_FALLBACK")

    if primary is None:
        raise ValueError("AI_PRIMARY_API_KEY is not set")

    backends = [b for b in (primary, fallback) if b is not None]
    return AIService(
        chat_backends=backends,
        stt_backends=backends

    )


ai_service = build_ai_service()