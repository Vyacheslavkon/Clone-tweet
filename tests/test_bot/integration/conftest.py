import asyncio

import httpx
import openai
import pytest
import respx
from pydantic import BaseModel

from services.client import Backend, AIService

PRIMARY = "https://primary.test/v1"
FALLBACK = "https://fallback.test/v1"
AUDIO = b"fake-ogg-audio-bytes"


SUMMARY = {
    "days_period": 7, "total_amount": 100, "total_count": 1,
    "categories": [], "top_items": [], "user_config": {"currency": "USD"},
}


def make_backend(name: str, base: str, stt_mode: str) -> Backend:
    return Backend(
        name=name,
        client=openai.AsyncOpenAI(api_key="test", base_url=base, max_retries=0, timeout=5),
        client_x=httpx.AsyncClient(
            base_url=base, headers={"Authorization": "Bearer test"}, timeout=5
        ),
        model="m",
        stt_mode=stt_mode,
        stt_model="whisper-1",
    )


def chat_ok(content: str = '{"ok": true}', finish: str = "stop") -> httpx.Response:
    return httpx.Response(200, json={
        "id": "x", "object": "chat.completion", "created": 1, "model": "m",
        "choices": [{"index": 0, "finish_reason": finish,
                     "message": {"role": "assistant", "content": content}}],
    })


def chat_route(api, base: str):
    return api.post(f"{base}/chat/completions")



class Tiny(BaseModel):
    ok: bool


@pytest.fixture
def service():
    return AIService(
        chat_backends=[
            make_backend("primary", PRIMARY, "base64_json"),
            make_backend("fallback", FALLBACK, "multipart"),
        ],
        stt_backends=[
            make_backend("primary", PRIMARY, "base64_json"),
            make_backend("fallback", FALLBACK, "multipart"),
        ],
    )


@pytest.fixture
def api():
    # fallback-маршруты часто остаются невызванными, это нормально
    with respx.mock(assert_all_called=False) as router:
        yield router



@pytest.fixture
async def silent_server():
    release = asyncio.Event()

    async def handle(reader, writer):
        await reader.read(65536)          # принять запрос
        await release.wait()              # и молчать до конца теста
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    yield port
    release.set()
    server.close()