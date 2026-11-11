import base64
import json

import httpx
import openai
import pytest

from services.exceptions import TruncatedResponseError
from tests.test_bot.integration.conftest import chat_route, PRIMARY, FALLBACK, chat_ok, Tiny, SUMMARY, AUDIO


async def test_primary_ok_fallback_untouched(service, api):
    p = chat_route(api, PRIMARY).mock(return_value=chat_ok())
    f = chat_route(api, FALLBACK).mock(return_value=chat_ok())

    result = await service.process_receipt(Tiny, "text", "en")

    assert result.ok is True
    assert p.call_count == 1
    assert f.call_count == 0


@pytest.mark.parametrize("status", [401, 402, 429, 500, 503])
async def test_availability_status_switches_to_fallback(service, api, status):
    p = chat_route(api, PRIMARY).mock(return_value=httpx.Response(status, json={"error": "x"}))
    f = chat_route(api, FALLBACK).mock(return_value=chat_ok())

    result = await service.process_receipt(Tiny, "text", "en")

    assert result.ok is True
    assert p.call_count == 1 and f.call_count == 1


@pytest.mark.parametrize("exc", [httpx.ConnectError("down"), httpx.ReadTimeout("slow")])
async def test_network_failure_switches_to_fallback(service, api, exc):
    chat_route(api, PRIMARY).mock(side_effect=exc)
    f = chat_route(api, FALLBACK).mock(return_value=chat_ok())

    assert (await service.process_receipt(Tiny, "text", "en")).ok is True
    assert f.call_count == 1


async def test_bad_request_does_not_switch(service, api):
    chat_route(api, PRIMARY).mock(return_value=httpx.Response(400, json={"error": "bad"}))
    f = chat_route(api, FALLBACK).mock(return_value=chat_ok())

    with pytest.raises(openai.BadRequestError):
        await service.process_receipt(Tiny, "text", "en")
    assert f.call_count == 0          # резерв не вызывался


async def test_empty_choices_with_status_200_switches(service, api):
    chat_route(api, PRIMARY).mock(return_value=httpx.Response(200, json={
        "id": "x", "object": "chat.completion", "created": 1, "model": "m", "choices": [],
    }))
    f = chat_route(api, FALLBACK).mock(return_value=chat_ok())

    assert (await service.process_receipt(Tiny, "text", "en")).ok is True
    assert f.call_count == 1


async def test_empty_content_switches(service, api):
    chat_route(api, PRIMARY).mock(return_value=chat_ok(content=""))
    f = chat_route(api, FALLBACK).mock(return_value=chat_ok())

    assert (await service.process_receipt(Tiny, "text", "en")).ok is True
    assert f.call_count == 1


async def test_truncated_response_does_not_switch(service, api):
    chat_route(api, PRIMARY).mock(return_value=chat_ok(finish="length"))
    f = chat_route(api, FALLBACK).mock(return_value=chat_ok())

    with pytest.raises(TruncatedResponseError):
        await service.process_receipt(Tiny, "text", "en")
    assert f.call_count == 0


async def test_all_backends_fail_raises_last_error(service, api):
    chat_route(api, PRIMARY).mock(side_effect=httpx.ConnectError("down"))
    chat_route(api, FALLBACK).mock(return_value=httpx.Response(503, json={"error": "x"}))

    with pytest.raises(openai.InternalServerError):
        await service.process_receipt(Tiny, "text", "en")


# ---------------------------------------------------------------- анализ

async def test_analysis_switches_to_fallback(service, api):
    chat_route(api, PRIMARY).mock(return_value=httpx.Response(429, json={"error": "x"}))
    f = chat_route(api, FALLBACK).mock(return_value=chat_ok())

    result = await service.analysis_financial(Tiny, SUMMARY, 7, 7, "en")

    assert result.ok is True
    assert f.call_count == 1


async def test_analysis_bad_request_does_not_switch(service, api):
    chat_route(api, PRIMARY).mock(return_value=httpx.Response(400, json={"error": "x"}))
    f = chat_route(api, FALLBACK).mock(return_value=chat_ok())

    with pytest.raises(openai.BadRequestError):
        await service.analysis_financial(Tiny, SUMMARY, 7, 7, "en")
    assert f.call_count == 0


# ---------------------------------------------------------------- STT

def stt_route(api, base: str):
    return api.post(f"{base}/audio/transcriptions")


async def test_stt_primary_sends_valid_base64_body(service, api):
    p = stt_route(api, PRIMARY).mock(return_value=httpx.Response(200, json={"text": "hello"}))
    f = stt_route(api, FALLBACK).mock(return_value=httpx.Response(200, json={"text": "other"}))

    assert await service._transcribe(AUDIO) == "hello"

    body = json.loads(p.calls.last.request.content)
    assert body["model"] == "whisper-1"
    assert body["input_audio"]["format"] == "ogg"
    assert base64.b64decode(body["input_audio"]["data"]) == AUDIO   # чистый base64, не data URI
    assert f.call_count == 0


@pytest.mark.parametrize("status", [401, 402, 429, 500])
async def test_stt_primary_failure_falls_back_with_full_audio(service, api, status):
    stt_route(api, PRIMARY).mock(return_value=httpx.Response(status, json={"error": "x"}))
    f = stt_route(api, FALLBACK).mock(return_value=httpx.Response(200, json={"text": "hello"}))

    assert await service._transcribe(AUDIO) == "hello"

    assert f.call_count == 1
    assert AUDIO in f.calls.last.request.content     # резерв получил файл целиком (multipart)


async def test_stt_primary_network_error_falls_back(service, api):
    stt_route(api, PRIMARY).mock(side_effect=httpx.ConnectError("down"))
    f = stt_route(api, FALLBACK).mock(return_value=httpx.Response(200, json={"text": "hello"}))

    assert await service._transcribe(AUDIO) == "hello"
    assert f.call_count == 1


async def test_stt_bad_format_400_does_not_switch(service, api):
    """400 (например, формат аудио) не лечится сменой провайдера."""
    stt_route(api, PRIMARY).mock(return_value=httpx.Response(400, json={"error": "format"}))
    f = stt_route(api, FALLBACK).mock(return_value=httpx.Response(200, json={"text": "x"}))

    with pytest.raises(httpx.HTTPStatusError):
        await service._transcribe(AUDIO)
    assert f.call_count == 0


async def test_stt_empty_text_switches(service, api):
    stt_route(api, PRIMARY).mock(return_value=httpx.Response(200, json={"text": ""}))
    f = stt_route(api, FALLBACK).mock(return_value=httpx.Response(200, json={"text": "hello"}))

    assert await service._transcribe(AUDIO) == "hello"
    assert f.call_count == 1


async def test_voice_pipeline_failover_end_to_end(service, api):
    """STT и чат уходят на резерв независимо друг от друга."""
    stt_route(api, PRIMARY).mock(return_value=httpx.Response(429, json={"error": "x"}))
    stt_route(api, FALLBACK).mock(return_value=httpx.Response(200, json={"text": "milk 100"}))
    chat_route(api, PRIMARY).mock(side_effect=httpx.ConnectError("down"))
    chat_route(api, FALLBACK).mock(return_value=chat_ok())

    result = await service.process_voice_message(AUDIO, "en", Tiny)

    assert result.ok is True