from datetime import datetime, timezone
from financial_bot.handlers.utils import  to_local_time, is_valid_timezone, format_transaction_card
from financial_bot.general_utils import get_today_boundaries_utc


def test_format_transaction_card_with_timezone(test_i18n):
    tx = {
        "category": "food", "amount": 500.0, "type": "expense",
        "created_at": "2026-09-24T20:00:00+00:00",
        "description": None, "items": [],
    }
    _ = test_i18n.gettext
    text = format_transaction_card(tx, _,  user_timezone="America/New_York")
    assert "16:00" in text


def test_format_transaction_card_shows_manual_description(test_i18n):
    tx = {
        "category": "food", "amount": 500.0, "type": "expense",
        "created_at": "2026-09-24T20:00:00+00:00",
        "description": "lunch with friends", "items": [],
    }
    _ = test_i18n.gettext
    text = format_transaction_card(tx, _, user_timezone="UTC")
    assert "lunch with friends" in text


def test_format_transaction_card_hides_type_leaked_as_description(test_i18n):
    """Регрессионный тест на баг, который вы нашли: description не должен
    показываться, если туда случайно попало 'expense'/'income'."""
    tx = {
        "category": "food", "amount": 500.0, "type": "expense",
        "created_at": "2026-09-24T20:00:00+00:00",
        "description": "", "items": [],
    }
    _ = test_i18n.gettext
    text = format_transaction_card(tx, _, user_timezone="UTC")
    assert "📝" not in text


def test_format_transaction_card_shows_voice_items(test_i18n):
    tx = {
        "category": "food", "amount": 1800.0, "type": "expense",
        "created_at": "2026-09-24T20:00:00+00:00",
        "description": None, "items": [{"name": "Bread", "price": 100}, {"name": "Milk", "price": 150}],
    }
    _ = test_i18n.gettext
    text = format_transaction_card(tx, _, user_timezone="UTC")
    assert "Bread" in text and "Milk" in text