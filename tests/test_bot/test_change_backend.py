import httpx
import openai
import pytest
from unittest.mock import AsyncMock

from services.client import AIService, Backend, ProviderResponseError, is_failover_error
from services.exceptions import TruncatedResponseError

REQ = httpx.Request("POST", "https://example.test/v1")


def conn_error():
    return openai.APIConnectionError(request=REQ)


def status_error(code: int):
    resp = httpx.Response(code, request=REQ)
    cls = {400: openai.BadRequestError, 429: openai.RateLimitError,
           401: openai.AuthenticationError}.get(code, openai.APIStatusError)
    return cls("err", response=resp, body=None)


def backend(name: str) -> Backend:
    return Backend(name=name, client=AsyncMock(), model="m",
                   client_x=AsyncMock, stt_model="x", stt_mode="f")


@pytest.fixture
def service():
    return AIService([backend("primary"), backend("fallback")], [backend("stt")])


async def test_primary_ok_fallback_not_called(service):
    calls = []
    async def call(b):
        calls.append(b.name)
        return "ok"
    assert await service._with_failover(service.chat_backends, "t", call) == "ok"
    assert calls == ["primary"]


async def test_connection_error_switches_to_fallback(service):
    async def call(b):
        if b.name == "primary":
            raise conn_error()
        return "from-fallback"
    assert await service._with_failover(service.chat_backends, "t", call) == "from-fallback"


@pytest.mark.parametrize("code", [401, 402, 429, 500, 503])
async def test_availability_status_codes_switch(service, code):
    async def call(b):
        if b.name == "primary":
            raise status_error(code)
        return "ok"
    assert await service._with_failover(service.chat_backends, "t", call) == "ok"


async def test_bad_request_does_not_switch(service):
    calls = []
    async def call(b):
        calls.append(b.name)
        raise status_error(400)
    with pytest.raises(openai.BadRequestError):
        await service._with_failover(service.chat_backends, "t", call)
    assert calls == ["primary"]            # резерв не вызывался


async def test_truncation_does_not_switch(service):
    calls = []
    async def call(b):
        calls.append(b.name)
        raise TruncatedResponseError("cut")
    with pytest.raises(TruncatedResponseError):
        await service._with_failover(service.chat_backends, "t", call)
    assert calls == ["primary"]


async def test_all_backends_fail_raises_last(service):
    async def call(b):
        raise conn_error() if b.name == "primary" else status_error(500)
    with pytest.raises(openai.APIStatusError):
        await service._with_failover(service.chat_backends, "t", call)


async def test_empty_choices_is_failover_error():
    assert is_failover_error(ProviderResponseError("empty"))


async def test_stt_fallback_receives_full_audio_after_primary_failure():
    audio = b"audio-bytes"
    received = {}
    client_x = AsyncMock()
    client = AsyncMock()
    primary =Backend("primary", client, client_x, "m", "base64_json", "f")
    primary.client_x.post = AsyncMock(side_effect=httpx.ConnectError("down"))

    fallback = Backend("fallback", client, client_x, "m", "multipart", "f")
    async def create(model, file, timeout):
        received["data"] = file.read()
        return type("T", (), {"text": "hello"})()
    fallback.client.audio.transcriptions.create = create

    svc = AIService([primary], [primary, fallback])
    assert await svc._transcribe(audio) == "hello"
    assert received["data"] == audio


async def test_close_closes_each_client_once():
    shared = AsyncMock()
    shared_x = AsyncMock()
    b1 = Backend("a", shared, shared_x, "m", "f", "h")
    b2 = Backend("b", shared, shared_x, "m", "f", "h")
    svc = AIService([b1], [b2])
    await svc.close()
    shared.close.assert_awaited_once()
    shared_x.aclose.assert_awaited_once()