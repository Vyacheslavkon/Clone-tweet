from collections import namedtuple
from decimal import Decimal

import pytest
from unittest.mock import AsyncMock, patch
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

from financial_bot.schemas import Plan
from financial_bot.tasks.vehicle_reports import send_weekly_stats_task, send_monthly_stats_task
from services.scheduled_reports import send_weekly_stats, send_monthly_stats
from tests.test_bot.conftest import make_user

TG_ID_1 = 111
TG_ID_2 = 222
TG_ID_3 = 333

async def test_send_weekly_stats_happy_path_all_users(
    mock_bot, mock_scheduled_reports_infra,
    mock_get_all_users, mock_get_reports_for_all_active_users,
    mock_blocked_users_bulk,
):
    users = [make_user(1, TG_ID_1), make_user(2, TG_ID_2)]
    mock_get_all_users.return_value = users
    mock_get_reports_for_all_active_users.return_value = {
        1: [], 2: [],
    }

    await send_weekly_stats()

    assert mock_bot.send_message.await_count == 2
    mock_blocked_users_bulk.assert_not_awaited()


async def test_send_weekly_stats_uses_correct_period_key(
    mock_bot, mock_scheduled_reports_infra,
    mock_get_all_users, mock_get_reports_for_all_active_users,
):
    users = [make_user(1, TG_ID_1)]
    mock_get_all_users.return_value = users
    mock_get_reports_for_all_active_users.return_value = {1: []}

    with patch("services.scheduled_reports.formatters", return_value="report text") as mock_formatters:
        await send_weekly_stats()

    _, kwargs = mock_formatters.call_args
    assert kwargs.get("period_key") == "week" or mock_formatters.call_args[0][2] == "week"


async def test_send_weekly_stats_forbidden_error_batches_block(
    mock_bot, mock_scheduled_reports_infra,
    mock_get_all_users, mock_get_reports_for_all_active_users,
    mock_blocked_users_bulk,
):
    users = [make_user(1, TG_ID_1), make_user(2, TG_ID_2)]
    mock_get_all_users.return_value = users
    mock_get_reports_for_all_active_users.return_value = {1: [], 2: []}

    mock_bot.send_message.side_effect = [
        TelegramForbiddenError(method="sendMessage", message="blocked"),
        AsyncMock(),
    ]

    await send_weekly_stats()

    mock_blocked_users_bulk.assert_awaited_once()
    args, _ = mock_blocked_users_bulk.call_args
    assert TG_ID_1 in args[1]
    assert TG_ID_2 not in args[1]



async def test_send_weekly_stats_no_users_blocked_skips_bulk_update(
    mock_bot, mock_scheduled_reports_infra,
    mock_get_all_users, mock_get_reports_for_all_active_users,
    mock_blocked_users_bulk,
):
    users = [make_user(1, TG_ID_1)]
    mock_get_all_users.return_value = users
    mock_get_reports_for_all_active_users.return_value = {1: []}

    await send_weekly_stats()

    mock_blocked_users_bulk.assert_not_awaited()


async def test_send_weekly_stats_generic_error_does_not_block_user(
    mock_bot, mock_scheduled_reports_infra,
    mock_get_all_users, mock_get_reports_for_all_active_users,
    mock_blocked_users_bulk,
):
    users = [make_user(1, TG_ID_1), make_user(2, TG_ID_2)]
    mock_get_all_users.return_value = users
    mock_get_reports_for_all_active_users.return_value = {1: [], 2: []}

    mock_bot.send_message.side_effect = [
        Exception("some unrelated network hiccup"),
        AsyncMock(),
    ]

    await send_weekly_stats()

    mock_blocked_users_bulk.assert_not_awaited()
    assert mock_bot.send_message.await_count == 2


async def test_send_weekly_stats_retry_after_waits_and_resends(
    mock_bot, mock_scheduled_reports_infra,
    mock_get_all_users, mock_get_reports_for_all_active_users,
):
    users = [make_user(1, TG_ID_1)]
    mock_get_all_users.return_value = users
    mock_get_reports_for_all_active_users.return_value = {1: []}

    mock_bot.send_message.side_effect = [
        TelegramRetryAfter(method="sendMessage", message="rate limited", retry_after=3),
        AsyncMock(),
    ]

    with patch("services.scheduled_reports.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await send_weekly_stats()

    mock_sleep.assert_any_await(3)
    assert mock_bot.send_message.await_count == 2


async def test_send_monthly_stats_includes_planning_block(
    mock_bot, mock_scheduled_reports_infra,
    mock_get_all_users, mock_get_reports_for_all_active_users,
    mock_get_plans_for_all_active_users,
):
    users = [make_user(1, TG_ID_1)]
    mock_get_all_users.return_value = users
    MockRow = namedtuple("MockRow", "type category total")
    mock_get_reports_for_all_active_users.return_value = {
        1:  [MockRow(type="expense", category="food", total=Decimal("1000"))]
    }
    mock_get_plans_for_all_active_users.return_value = {
        1: Plan(monthly_budget=Decimal("5000"), budget_remind_percent=Decimal("80"), savings_goal=None)
    }

    await send_monthly_stats()

    _, kwargs = mock_bot.send_message.call_args
    assert "Planning" in kwargs["text"]
    assert "Planned budget" in kwargs["text"]


async def test_send_monthly_stats_uses_month_name_not_generic_month_word(
    mock_bot, mock_scheduled_reports_infra,
    mock_get_all_users, mock_get_reports_for_all_active_users,
    mock_get_plans_for_all_active_users,
):

    users = [make_user(1, TG_ID_1)]
    mock_get_all_users.return_value = users
    mock_get_reports_for_all_active_users.return_value = {1: []}
    mock_get_plans_for_all_active_users.return_value = {1: None}

    with patch(
        "services.scheduled_reports.get_month_name", return_value="September"
    ) as mock_get_month_name:
        await send_monthly_stats()

    mock_get_month_name.assert_called_once()
    _, kwargs = mock_bot.send_message.call_args
    assert "September" in kwargs["text"]


def test_send_weekly_stats_task_delegates_to_worker_loop(celery_eager):
    with patch("financial_bot.tasks.vehicle_reports.send_weekly_stats", new_callable=AsyncMock) as mock_fn:
        result = send_weekly_stats_task.delay()

    assert result.successful()
    mock_fn.assert_awaited_once()


@pytest.mark.parametrize("celery_eager", [False], indirect=True)
def test_send_weekly_stats_task_failure_is_visible_to_celery(celery_eager):
    with patch(
        "financial_bot.tasks.vehicle_reports.send_weekly_stats",
        side_effect=Exception("db connection lost"),
    ):
        result = send_weekly_stats_task.delay()

    assert result.failed()
    assert isinstance(result.result, Exception)