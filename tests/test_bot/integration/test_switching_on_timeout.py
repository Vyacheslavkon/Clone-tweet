import asyncio
import time

import httpx
import openai

from services.client import Backend, AIService
from tests.test_bot.integration.conftest import chat_ok, FALLBACK, Tiny


async def test_silent_primary_times_out_and_falls_back(silent_server):
    def fallback_handler(request: httpx.Request) -> httpx.Response:
        return chat_ok()

    primary = Backend(
        name="primary",
        client=openai.AsyncOpenAI(
            api_key="t", base_url=f"http://127.0.0.1:{silent_server}/v1",
            timeout=0.5, max_retries=0,
        ),
        client_x=httpx.AsyncClient(timeout=0.5),
        model="m", stt_mode="multipart", stt_model="whisper-1",
    )
    fallback = Backend(
        name="fallback",
        client=openai.AsyncOpenAI(
            api_key="t", base_url=FALLBACK, max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(fallback_handler)),
        ),
        client_x=httpx.AsyncClient(),
        model="m", stt_mode="multipart", stt_model="whisper-1",
    )
    svc = AIService([primary, fallback], [primary])

    started = time.monotonic()
    result = await svc.process_receipt(Tiny, "text", "en")
    elapsed = time.monotonic() - started

    assert result.ok is True
    assert 0.4 < elapsed < 3          # дождались таймаут и ушли на резерв, а не повисли