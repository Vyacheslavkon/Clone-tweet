import pytest
from unittest.mock import AsyncMock, patch
import openai
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError

from financial_bot.tasks.ai import process_analysis_expense_task
from tests.test_bot.conftest import ANALYSIS_SCHEMA_FACTORIES, make_weekly_analysis_response

TG_ID = 1328587577
CHAT_ID = 1328587577

@pytest.fixture(autouse=True)
def _configure_isolated_session(mock_isolated_session):
    """В process_analysis_financial сессия открывается безусловно в начале
    функции — настраиваем return_value один раз для всех тестов этого файла."""
    mock_isolated_session.return_value = AsyncMock()


@pytest.mark.parametrize("days", [7, 30])
def test_analysis_cache_hit_skips_ai_call(
    days, celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_cache_service_analysis, mock_analysis_ai_service,
):

    response_schema_cls, min_items, make_response = ANALYSIS_SCHEMA_FACTORIES[days]

    fake_user = AsyncMock(id=42, language_code="en")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(min_items)],
        "days_period": days,
    }
    cached_result = make_response(summary="cached summary")
    mock_cache_service_analysis.get_cached_analysis.return_value = cached_result

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=days, locale="en",
    )

    assert result.successful()
    mock_analysis_ai_service.assert_not_awaited()
    mock_bot.send_message.assert_awaited_once()


@pytest.mark.parametrize("days", [7, 30])
def test_analysis_cache_miss_calls_ai_and_writes_cache(
    days, celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_cache_service_analysis, mock_analysis_ai_service,
):
    response_schema_cls, min_items, make_response = ANALYSIS_SCHEMA_FACTORIES[days]

    fake_user = AsyncMock(id=42, language_code="en")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(min_items)],
        "days_period": days,
    }
    mock_cache_service_analysis.get_cached_analysis.return_value = None
    fresh_result = make_response(summary="fresh summary")
    mock_analysis_ai_service.return_value = fresh_result

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=days, locale="en",
    )

    assert result.successful()
    mock_analysis_ai_service.assert_awaited_once()
    mock_cache_service_analysis.set_analysis_cache.assert_awaited_once_with(
        fake_user.id, days, fresh_result
    )
    mock_bot.send_message.assert_awaited_once()



def test_analysis_no_data_sends_early_message(
    celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_analysis_ai_service,
):
    fake_user = AsyncMock(id=42, language_code="en")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = None

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=7, locale="en",
    )

    assert result.successful()
    mock_analysis_ai_service.assert_not_awaited()
    mock_bot.send_message.assert_awaited_once()
    _, kwargs = mock_bot.send_message.call_args
    assert "enough transactions" in kwargs["text"]


@pytest.mark.parametrize(
    "days,items_count",
    [
        (7, 2),
        (30, 8),
    ],
)

def test_analysis_not_enough_items_sends_early_message(
    days, items_count,
    celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_analysis_ai_service,
):
    fake_user = AsyncMock(id=42, language_code="en")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(items_count)],
        "days_period": days,
    }

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=days, locale="en",
    )

    assert result.successful()
    mock_analysis_ai_service.assert_not_awaited()
    mock_bot.send_message.assert_awaited_once()
    _, kwargs = mock_bot.send_message.call_args
    assert "Not enough data" in kwargs["text"]


@pytest.mark.parametrize("days,min_items", [(7, 5), (30, 12)])
def test_analysis_threshold_differs_by_period(
    days, min_items, celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_analysis_ai_service,
):

    fake_user = AsyncMock(id=42, language_code="en")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(min_items - 1)],         "days_period": days,
    }

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=days, locale="en",
    )

    assert result.successful()
    mock_analysis_ai_service.assert_not_awaited()


def test_analysis_survives_cache_read_failure(
    celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_cache_service_analysis, mock_analysis_ai_service,
):
    fake_user = AsyncMock(id=42, language_code="en")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(5)],
        "days_period": 7,
    }
    mock_cache_service_analysis.get_cached_analysis.side_effect = ConnectionError("redis down")
    mock_analysis_ai_service.return_value = make_weekly_analysis_response(summary="ok")

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=7, locale="en",
    )

    assert result.successful()
    mock_analysis_ai_service.assert_awaited_once()
    mock_bot.send_message.assert_awaited_once()


def test_analysis_survives_cache_write_failure(
    celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_cache_service_analysis, mock_analysis_ai_service,
):
    fake_user = AsyncMock(id=42, language_code="en")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(5)],
        "days_period": 7,
    }
    mock_cache_service_analysis.get_cached_analysis.return_value = None
    mock_cache_service_analysis.set_analysis_cache.side_effect = ConnectionError("redis down")
    mock_analysis_ai_service.return_value = make_weekly_analysis_response(summary="ok")

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=7, locale="en",
    )

    assert result.successful()
    mock_bot.send_message.assert_awaited_once()


@pytest.mark.parametrize("celery_eager", [False], indirect=True)
def test_analysis_retries_on_openai_error(
    celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_cache_service_analysis, mock_analysis_ai_service,
):
    fake_user = AsyncMock(id=42, language_code="en")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(6)],
        "days_period": 7,
    }
    mock_cache_service_analysis.get_cached_analysis.return_value = None
    mock_analysis_ai_service.side_effect = openai.APITimeoutError("timeout")

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=7, locale="en",
    )

    assert mock_analysis_ai_service.call_count == process_analysis_expense_task.max_retries + 1
    assert result.failed()
    assert isinstance(result.result, openai.OpenAIError)
    mock_bot.send_message.assert_awaited_once()
    _, kwargs = mock_bot.send_message.call_args
    assert "couldn't generate your financial analysis" in kwargs["text"]


def test_analysis_forbidden_error_silently_skips(
    celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_cache_service_analysis,
):
    fake_user = AsyncMock(id=42, language_code="en")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(5)],
        "days_period": 7,
    }
    mock_cache_service_analysis.get_cached_analysis.return_value = make_weekly_analysis_response(summary="ok")
    mock_bot.send_message.side_effect = TelegramForbiddenError(method="sendMessage", message="bot blocked")

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=7, locale="en",
    )

    assert result.successful()
    mock_bot.send_message.assert_awaited_once()


def test_analysis_bad_request_sends_fallback_message(
    celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_cache_service_analysis,
):
    fake_user = AsyncMock(id=42, language_code="en")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(5)],
        "days_period": 7,
    }
    mock_cache_service_analysis.get_cached_analysis.return_value = make_weekly_analysis_response(summary="ok")


    mock_bot.send_message.side_effect = [
        TelegramBadRequest(method="sendMessage", message="message is too long"),
        AsyncMock(),
    ]

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=7, locale="en",
    )

    assert result.successful()
    assert mock_bot.send_message.call_count == 2
    _, kwargs = mock_bot.send_message.call_args
    assert "couldn't display it properly" in kwargs["text"]


def test_analysis_generic_telegram_error_sends_fallback_and_succeeds(
    celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_cache_service_analysis,
):
    fake_user = AsyncMock(id=42, language_code="en")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(5)],
        "days_period": 7,
    }
    mock_cache_service_analysis.get_cached_analysis.return_value = make_weekly_analysis_response(summary="ok")

    mock_bot.send_message.side_effect = [
        TelegramAPIError(method="sendMessage", message="network error"),
        AsyncMock(),
    ]

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=7, locale="en",
    )

    assert result.successful()
    assert mock_bot.send_message.call_count == 2
    _, kwargs = mock_bot.send_message.call_args
    assert "couldn't deliver your analysis" in kwargs["text"]


@pytest.mark.parametrize("celery_eager", [False], indirect=True)
def test_analysis_rendering_failure_reraises_for_celery_monitoring(
    celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_cache_service_analysis,
):
    fake_user = AsyncMock(id=42, language_code="en")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(5)],
        "days_period": 7,
    }
    mock_cache_service_analysis.get_cached_analysis.return_value = make_weekly_analysis_response(summary="ok")

    with patch(
        "services.pipelines.render_analysis_report",
        side_effect=ValueError("unexpected rendering bug"),
    ):
        result = process_analysis_expense_task.delay(
            tg_id=TG_ID, chat_id=CHAT_ID, days=7, locale="en",
        )

    assert result.failed()
    assert isinstance(result.result, ValueError)
    mock_bot.send_message.assert_awaited_once()


