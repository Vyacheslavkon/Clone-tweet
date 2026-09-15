import pytest
from unittest.mock import AsyncMock, patch
from celery.exceptions import Retry
import openai
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError

from financial_bot.tasks.ai import process_analysis_expense_task
from services.schemas import WeeklyAnalysisResponse, MonthlyAnalysisResponse
from tests.test_bot.conftest import ANALYSIS_SCHEMA_FACTORIES

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
    #mock_isolated_session.return_value = AsyncMock()

    response_schema_cls, min_items, make_response = ANALYSIS_SCHEMA_FACTORIES[days]

    fake_user = AsyncMock(id=42, language_code="ru")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(min_items)],
        "days_period": days,
    }
    cached_result = make_response(summary="cached summary")
    mock_cache_service_analysis.get_cached_analysis.return_value = cached_result

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=days, locale="ru",
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

    fake_user = AsyncMock(id=42, language_code="ru")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(6)],
        "days_period": 7,
    }
    mock_cache_service_analysis.get_cached_analysis.return_value = None
    fresh_result = make_response(summary="fresh summary")
    mock_analysis_ai_service.return_value = fresh_result

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=7, locale="ru",
    )

    assert result.successful()
    mock_analysis_ai_service.assert_awaited_once()
    mock_cache_service_analysis.set_analysis_cache.assert_awaited_once_with(
        fake_user.id, 7, fresh_result
    )
    mock_bot.send_message.assert_awaited_once()


# unverified

def test_analysis_no_data_sends_early_message(
    celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_analysis_ai_service,
):
    fake_user = AsyncMock(id=42, language_code="ru")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = None

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=7, locale="ru",
    )

    assert result.successful()
    mock_analysis_ai_service.assert_not_awaited()
    mock_bot.send_message.assert_awaited_once()
    _, kwargs = mock_bot.send_message.call_args
    assert "enough transactions" in kwargs["text"]


# ---------- Недостаточно items для глубокого анализа ----------

def test_analysis_not_enough_items_sends_early_message(
    celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_analysis_ai_service,
):
    fake_user = AsyncMock(id=42, language_code="ru")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": "item1"}, {"name": "item2"}],  # меньше 5 для weekly
        "days_period": 7,
    }

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=7, locale="ru",
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
    """Проверяем, что порог действительно разный для недели (5) и месяца (12)."""
    fake_user = AsyncMock(id=42, language_code="ru")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(min_items - 1)],  # на 1 меньше порога
        "days_period": days,
    }

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=days, locale="ru",
    )

    assert result.successful()
    mock_analysis_ai_service.assert_not_awaited()  # ниже порога — AI не вызывается


# ---------- Устойчивость к сбою чтения кэша ----------

def test_analysis_survives_cache_read_failure(
    celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_cache_service_analysis, mock_analysis_ai_service,
):
    fake_user = AsyncMock(id=42, language_code="ru")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(6)],
        "days_period": 7,
    }
    mock_cache_service_analysis.get_cached_analysis.side_effect = ConnectionError("redis down")
    mock_analysis_ai_service.return_value = WeeklyAnalysisResponse(summary="ok")

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=7, locale="ru",
    )

    assert result.successful()
    mock_analysis_ai_service.assert_awaited_once()  # флоу продолжился, несмотря на сбой кэша
    mock_bot.send_message.assert_awaited_once()


# ---------- Устойчивость к сбою записи в кэш ----------

def test_analysis_survives_cache_write_failure(
    celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_cache_service_analysis, mock_analysis_ai_service,
):
    fake_user = AsyncMock(id=42, language_code="ru")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(6)],
        "days_period": 7,
    }
    mock_cache_service_analysis.get_cached_analysis.return_value = None
    mock_cache_service_analysis.set_analysis_cache.side_effect = ConnectionError("redis down")
    mock_analysis_ai_service.return_value = WeeklyAnalysisResponse(summary="ok")

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=7, locale="ru",
    )

    assert result.successful()  # сбой записи кэша не должен ронять задачу
    mock_bot.send_message.assert_awaited_once()


# ---------- OpenAI сбой -> retry ----------

@pytest.mark.parametrize("celery_eager", [False], indirect=True)
def test_analysis_retries_on_openai_error(
    celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_cache_service_analysis, mock_analysis_ai_service,
):
    fake_user = AsyncMock(id=42, language_code="ru")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(6)],
        "days_period": 7,
    }
    mock_cache_service_analysis.get_cached_analysis.return_value = None
    mock_analysis_ai_service.side_effect = openai.APITimeoutError("timeout")

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=7, locale="ru",
    )

    assert mock_analysis_ai_service.call_count == process_analysis_expense_task.max_retries + 1
    assert result.failed()
    assert isinstance(result.result, openai.OpenAIError)
    mock_bot.send_message.assert_awaited_once()  # финальное уведомление о провале
    _, kwargs = mock_bot.send_message.call_args
    assert "couldn't generate your financial analysis" in kwargs["text"]

# TelegramApiError

def test_analysis_forbidden_error_silently_skips(
    celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_cache_service_analysis,
):
    fake_user = AsyncMock(id=42, language_code="ru")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(6)],
        "days_period": 7,
    }
    mock_cache_service_analysis.get_cached_analysis.return_value = WeeklyAnalysisResponse(summary="ok")
    mock_bot.send_message.side_effect = TelegramForbiddenError(method="sendMessage", message="bot blocked")

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=7, locale="ru",
    )

    assert result.successful()
    mock_bot.send_message.assert_awaited_once()  # только одна попытка, без retry-сообщения


def test_analysis_bad_request_sends_fallback_message(
    celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_cache_service_analysis,
):
    fake_user = AsyncMock(id=42, language_code="ru")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(6)],
        "days_period": 7,
    }
    mock_cache_service_analysis.get_cached_analysis.return_value = WeeklyAnalysisResponse(summary="ok")

    # Первый вызов (основной отчёт) падает, второй (fallback) успешен
    mock_bot.send_message.side_effect = [
        TelegramBadRequest(method="sendMessage", message="message is too long"),
        AsyncMock(),
    ]

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=7, locale="ru",
    )

    assert result.successful()
    assert mock_bot.send_message.call_count == 2  # основная попытка + fallback
    _, kwargs = mock_bot.send_message.call_args
    assert "couldn't display it properly" in kwargs["text"]


def test_analysis_generic_telegram_error_sends_fallback_and_succeeds(
    celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_cache_service_analysis,
):
    fake_user = AsyncMock(id=42, language_code="ru")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(6)],
        "days_period": 7,
    }
    mock_cache_service_analysis.get_cached_analysis.return_value = WeeklyAnalysisResponse(summary="ok")

    mock_bot.send_message.side_effect = [
        TelegramAPIError(method="sendMessage", message="network error"),
        AsyncMock(),
    ]

    result = process_analysis_expense_task.delay(
        tg_id=TG_ID, chat_id=CHAT_ID, days=7, locale="ru",
    )

    assert result.successful()
    assert mock_bot.send_message.call_count == 2
    _, kwargs = mock_bot.send_message.call_args
    assert "couldn't deliver your analysis" in kwargs["text"]


def test_analysis_rendering_failure_reraises_for_celery_monitoring(
    celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_get_user_by_id, mock_get_user_financial_summary,
    mock_cache_service_analysis,
):
    """Проверяем недавно добавленный raise: непредвиденный сбой рендеринга
    должен быть виден Celery как FAILURE, не проглатываться молча."""
    fake_user = AsyncMock(id=42, language_code="ru")
    mock_get_user_by_id.return_value = fake_user
    mock_get_user_financial_summary.return_value = {
        "top_items": [{"name": f"item{i}"} for i in range(6)],
        "days_period": 7,
    }
    mock_cache_service_analysis.get_cached_analysis.return_value = WeeklyAnalysisResponse(summary="ok")

    with patch(
        "services.pipelines.render_analysis_report",
        side_effect=ValueError("unexpected rendering bug"),
    ):
        result = process_analysis_expense_task.delay(
            tg_id=TG_ID, chat_id=CHAT_ID, days=7, locale="ru",
        )

    assert result.failed()
    assert isinstance(result.result, ValueError)
    mock_bot.send_message.assert_awaited_once()  # уведомление ушло, ошибка тоже видна


