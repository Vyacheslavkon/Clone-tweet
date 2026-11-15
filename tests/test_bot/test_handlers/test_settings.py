import json
import re
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from financial_bot.general_utils import get_today_boundaries_utc
from financial_bot.handlers.utils import is_valid_timezone, to_local_time
from financial_bot.states.settings_states import SettingsState
from services.client import AIService
from services.prompts import get_analysis_financial
from services.schemas import (
    MonthlyAnalysisResponse,
    ReceiptListAnalysisSchema,
    WeeklyAnalysisResponse,
)
from tests.test_bot.conftest import summary_data


def test_to_local_time_converts_correctly():
    dt_utc = datetime(2026, 9, 24, 20, 0, tzinfo=timezone.utc)
    local = to_local_time(dt_utc, "America/New_York")
    assert local.hour == 16


def test_to_local_time_invalid_timezone_falls_back_to_utc():
    dt_utc = datetime(2026, 9, 24, 20, 0, tzinfo=timezone.utc)
    local = to_local_time(dt_utc, "Not/AValidZone")
    assert local == dt_utc  # fallback


def test_get_today_boundaries_respects_timezone():
    start_utc, end_utc = get_today_boundaries_utc("America/New_York")

    assert start_utc.hour != 0 or start_utc.minute != 0


def test_get_today_boundaries_invalid_timezone_falls_back_to_utc():
    start_utc, end_utc = get_today_boundaries_utc("Invalid/Zone")
    assert start_utc.hour == 0
    assert start_utc.minute == 0


def test_is_valid_timezone():
    assert is_valid_timezone("Europe/Moscow") is True
    assert is_valid_timezone("Not/AValidZone") is False


async def test_timezone_selected_from_list(
    test_dp, mock_bot, create_mock_update, test_session, test_user, cache_service
):
    _, create_callback = create_mock_update
    user_id = test_user.tg_id

    await test_dp.feed_update(
        mock_bot, create_callback("set_tz:Europe/Moscow", user_id, 1)
    )

    await test_session.refresh(test_user)
    assert test_user.timezone == "Europe/Moscow"


async def test_timezone_manual_input_valid(
    test_dp, mock_bot, create_mock_update, test_session, test_user
):
    create_message, create_callback = create_mock_update
    user_id = test_user.tg_id

    await test_dp.feed_update(mock_bot, create_callback("set_tz_manual", user_id, 1))
    state = test_dp.fsm.get_context(bot=mock_bot, user_id=user_id, chat_id=user_id)
    assert await state.get_state() == SettingsState.waiting_for_custom_timezone.state

    await test_dp.feed_update(mock_bot, create_message("Asia/Tokyo", user_id, 2))

    await test_session.refresh(test_user)
    assert test_user.timezone == "Asia/Tokyo"
    assert await state.get_state() is None


@pytest.mark.parametrize("bad_value", ["NotARealZone", "../../etc/passwd", "America"])
async def test_timezone_manual_input_invalid_keeps_state(
    bad_value, test_dp, mock_bot, create_mock_update, test_session, test_user
):
    create_message, create_callback = create_mock_update
    user_id = test_user.tg_id
    original_tz = test_user.timezone

    await test_dp.feed_update(mock_bot, create_callback("set_tz_manual", user_id, 1))
    await test_dp.feed_update(mock_bot, create_message(bad_value, user_id, 2))

    state = test_dp.fsm.get_context(bot=mock_bot, user_id=user_id, chat_id=user_id)
    assert await state.get_state() == SettingsState.waiting_for_custom_timezone.state
    await test_session.refresh(test_user)
    assert test_user.timezone == original_tz


async def test_timezone_manual_cancel_clears_state(
    test_dp, mock_bot, create_mock_update, test_user
):
    create_message, create_callback = create_mock_update
    user_id = test_user.tg_id

    await test_dp.feed_update(mock_bot, create_callback("set_tz_manual", user_id, 1))
    await test_dp.feed_update(mock_bot, create_message("cancel", user_id, 2))

    state = test_dp.fsm.get_context(bot=mock_bot, user_id=user_id, chat_id=user_id)
    assert await state.get_state() is None


CYRILLIC = re.compile(r"[а-яА-ЯёЁ]")


def test_analysis_context_has_no_russian_boilerplate_for_english_locale():
    ctx = AIService.build_user_context(summary_data, locale="en")

    assert not CYRILLIC.search(ctx)


@pytest.mark.parametrize("locale,name", [("en", "English"), ("ru", "Russian")])
def test_language_named_in_prompt_and_context(locale, name):

    assert name in get_analysis_financial(30, 30, locale)
    assert name in AIService.build_user_context(summary_data, locale)


def test_schemas_have_no_cyrillic_descriptions():

    for schema in (
        WeeklyAnalysisResponse,
        MonthlyAnalysisResponse,
        ReceiptListAnalysisSchema,
    ):
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        assert not CYRILLIC.search(
            schema_json
        ), f"{schema.__name__} contains Cyrillic text in its schema"


@pytest.mark.parametrize("currency", ["RUB", "USD", "EUR"])
async def test_currency_selected_from_list(
    currency, test_dp, mock_bot, create_mock_update, test_session, test_user
):
    _, create_callback = create_mock_update
    await test_dp.feed_update(
        mock_bot, create_callback(f"set_cur:{currency}", test_user.tg_id, 1)
    )
    await test_session.refresh(test_user)
    assert test_user.currency == currency


@pytest.mark.parametrize("bad_code", ["XYZ", "rub", "../USD", ""])
async def test_currency_forged_callback_rejected(
    bad_code, test_dp, mock_bot, create_mock_update, test_session, test_user
):
    _, create_callback = create_mock_update
    original = test_user.currency
    await test_dp.feed_update(
        mock_bot, create_callback(f"set_cur:{bad_code}", test_user.tg_id, 1)
    )
    await test_session.refresh(test_user)
    assert test_user.currency == original


async def test_currency_change_invalidates_cache(
    test_dp, mock_bot, create_mock_update, test_user, cache_service
):
    _, create_callback = create_mock_update
    cache_service.invalidate_user_cache = AsyncMock()
    await test_dp.feed_update(
        mock_bot, create_callback("set_cur:USD", test_user.tg_id, 1)
    )
    cache_service.invalidate_user_cache.assert_awaited_once_with(user_id=test_user.id)
