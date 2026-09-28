from datetime import datetime, timezone

import pytest

from financial_bot.handlers.utils import  to_local_time, is_valid_timezone
from financial_bot.general_utils import get_today_boundaries_utc
from financial_bot.states.settings_states import SettingsState


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

    await test_dp.feed_update(mock_bot, create_callback("set_tz:Europe/Moscow", user_id, 1))

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
