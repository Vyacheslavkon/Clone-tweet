import json

import pytest
import openai
import uuid
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from celery.exceptions import Retry, MaxRetriesExceededError
from sqlalchemy import select, func
from sqlalchemy.util import await_only

from financial_bot.repositories import create_user
from financial_bot.schemas import CreateUser
from financial_bot.tasks.ai import process_expense_task
from services.schemas import ReceiptListAnalysisSchema, ReceiptAnalysisSchema, ReceiptItemSchema
from financial_bot.models import Transactions, UserBot
from services.pipelines import async_process_receipt
from services.celery_app import app as celery_app

async def test_process_expense_task_writes_to_real_db(mock_ai_service, mock_bot,
                                                      test_session_for_pipeline,
                                                      user_for_pipeline,
                                                      fake_analysis
                                                      ):

    user_id = user_for_pipeline.id
    chat_id = 11111

    mock_ai_service.return_value = fake_analysis

    await async_process_receipt(
        chat_id=chat_id,
        db_user_id=user_id,
        locale="ru",
        voice_bytes=b"fake_voice_binary_data"
    )


    stmt = select(Transactions).where(Transactions.user_id == user_id)
    result = await test_session_for_pipeline.execute(stmt)
    db_transactions = result.scalars().all()

    assert len(db_transactions) == 1
    assert db_transactions[0].amount == 250.0
    assert db_transactions[0].category == "food"
    assert db_transactions[0].batch_id is not None

    mock_bot.send_message.assert_called_once()
    call_kwargs = mock_bot.send_message.call_args.kwargs
    assert call_kwargs["chat_id"] == chat_id
    assert "250" in call_kwargs["text"]
    assert call_kwargs["reply_markup"] is not None



def test_process_expense_task_success():

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

    fake_voice = b"fake_ogg_voice_bytes"
    expected_output = {"status": "success", "extracted_amount": 500.0}

    with patch("financial_bot.tasks.ai.async_process_receipt", new_callable=AsyncMock) as mock_pipeline:
        mock_pipeline.return_value = expected_output

        result = process_expense_task.delay(
            chat_id=12345,
            db_user_id=42,
            locale="ru",
            voice_bytes=fake_voice
        )

        assert result.successful()
        assert result.result == expected_output
        mock_pipeline.assert_called_once_with(12345, 42, "ru", fake_voice)



def test_process_expense_task_retry_on_openai_error():

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = False

    with patch("financial_bot.tasks.ai.async_process_receipt", new_callable=AsyncMock) as mock_pipeline:

        mock_pipeline.side_effect = openai.OpenAIError("Rate limit exceeded")

        result = process_expense_task.delay(
            chat_id=12345,
            db_user_id=42,
            locale="ru",
            voice_bytes=b""
        )


        assert mock_pipeline.call_count == 4
        assert result.failed()


def test_process_expense_task_network_error_rolls_back_db():

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = False

    mock_worker_session = AsyncMock()

    session_created = False

    def side_effect_session():
        nonlocal session_created
        session_created = True
        return mock_worker_session

    with patch("services.utils_pipelines.get_isolated_session", side_effect=side_effect_session), \
            patch("services.client.ai_service.process_voice_message", new_callable=AsyncMock) as mock_openai_call:

        mock_openai_call.side_effect = openai.APITimeoutError("Request timed out")

        result = process_expense_task.delay(
            chat_id=12345,
            db_user_id=42,
            locale="ru",
            voice_bytes=b"dummy_voice"
        )

        if session_created:
            mock_worker_session.rollback.assert_called()
            assert mock_worker_session.__aexit__.called
        else:
            mock_worker_session.__aenter__.assert_not_called()
            mock_worker_session.rollback.assert_not_called()

        assert mock_openai_call.call_count == 4
        assert result.failed()


async def test_process_expense_task_garbage_audio_sends_joke_and_no_db_write(test_session_for_pipeline):

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

    mock_ai_response = ReceiptListAnalysisSchema(
        is_shopping_related=False,
        error_message="Красиво поёшь! Но где тут траты? Давай ближе к делу.",
        transactions=[]
    )

    # 3. Подменяем сессию воркера на нашу тестовую сессию из фикстуры,
    # мокаем ИИ и мокаем отправку сообщений ботом (например, bot.send_message)
    with patch("services.utils_pipelines.get_isolated_session", return_value=test_session_for_pipeline), \
            patch("services.client.ai_service.process_voice_message", new_callable=AsyncMock,
                  return_value=mock_ai_response), \
            patch("services.pipelines.async_process_receipt.Bot.send_message", new_callable=AsyncMock) as mock_send_message:

        result = process_expense_task.delay(
            chat_id=12345,
            db_user_id=42,
            locale="ru",
            voice_bytes=b"garbage_audio_bytes"
        )

        # 5. ПРОВЕРКИ

        # Задача должна завершиться успешно (без ретраев)
        assert result.successful()

        # Бот должен отправить пользователю именно ту шутку, которую сгенерировал ИИ
        mock_send_message.assert_called_once_with(
            chat_id=12345,
            text="Красиво поёшь! Но где тут траты? Давай ближе к делу."
        )

        # Проверяем, что в базе данных не появилось транзакций для этого пользователя
        # (Замените названия таблиц/колонок на ваши реальные)
        query = select(func.count()).select_from(Transactions).where(Transactions.user_id == 42)
        db_result = await test_session_for_pipeline.execute(query)
        transactions_count = db_result.scalar()

        assert transactions_count == 0