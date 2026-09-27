from datetime import datetime, timezone
from financial_bot.handlers.utils import  to_local_time, is_valid_timezone
from financial_bot.general_utils import get_today_boundaries_utc


def test_to_local_time_converts_correctly():
    dt_utc = datetime(2026, 9, 24, 20, 0, tzinfo=timezone.utc)
    local = to_local_time(dt_utc, "America/New_York")
    assert local.hour == 16  # UTC-4 (летнее время)


def test_to_local_time_invalid_timezone_falls_back_to_utc():
    dt_utc = datetime(2026, 9, 24, 20, 0, tzinfo=timezone.utc)
    local = to_local_time(dt_utc, "Not/AValidZone")
    assert local == dt_utc  # fallback


def test_get_today_boundaries_respects_timezone():
    start_utc, end_utc = get_today_boundaries_utc("America/New_York")
    # Полночь по Нью-Йорку — это НЕ полночь по UTC (сдвиг на 4-5 часов)
    assert start_utc.hour != 0 or start_utc.minute != 0


def test_get_today_boundaries_invalid_timezone_falls_back_to_utc():
    start_utc, end_utc = get_today_boundaries_utc("Invalid/Zone")
    assert start_utc.hour == 0
    assert start_utc.minute == 0


def test_is_valid_timezone():
    assert is_valid_timezone("Europe/Moscow") is True
    assert is_valid_timezone("Not/AValidZone") is False