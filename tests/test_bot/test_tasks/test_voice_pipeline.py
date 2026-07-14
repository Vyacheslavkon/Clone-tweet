import uuid
from unittest.mock import AsyncMock, patch

import openai
from sqlalchemy import func, select

from financial_bot.models import TransactionItems, Transactions
from financial_bot.repositories import delete_check, save_receipt_to_db
from financial_bot.tasks.ai import process_expense_task
from services.celery_app import app as celery_app
from services.pipelines import async_process_receipt
from services.schemas import (
    ReceiptListAnalysisSchema,
)
from services.utils_pipelines import merge_transactions_by_category


async def test_process_expense_task_writes_to_real_db(
    mock_ai_service,
    mock_bot,
    test_session_for_pipeline,
    user_for_pipeline,
    fake_analysis,
):

    user_id = user_for_pipeline.id
    chat_id = 11111

    mock_ai_service.return_value = fake_analysis

    await async_process_receipt(
        chat_id=chat_id,
        db_user_id=user_id,
        locale="ru",
        voice_bytes=b"fake_voice_binary_data",
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

    with patch(
        "financial_bot.tasks.ai.async_process_receipt", new_callable=AsyncMock
    ) as mock_pipeline:
        mock_pipeline.return_value = expected_output

        result = process_expense_task.delay(
            chat_id=12345, db_user_id=42, locale="ru", voice_bytes=fake_voice
        )

        assert result.successful()
        assert result.result == expected_output
        mock_pipeline.assert_called_once_with(12345, 42, "ru", fake_voice)


def test_process_expense_task_retry_on_openai_error():

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = False

    with patch(
        "financial_bot.tasks.ai.async_process_receipt", new_callable=AsyncMock
    ) as mock_pipeline:

        mock_pipeline.side_effect = openai.OpenAIError("Rate limit exceeded")

        result = process_expense_task.delay(
            chat_id=12345, db_user_id=42, locale="ru", voice_bytes=b""
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

    with patch(
        "services.utils_pipelines.get_isolated_session", side_effect=side_effect_session
    ), patch(
        "services.client.ai_service.process_voice_message", new_callable=AsyncMock
    ) as mock_openai_call:

        mock_openai_call.side_effect = openai.APITimeoutError("Request timed out")

        result = process_expense_task.delay(
            chat_id=12345, db_user_id=42, locale="ru", voice_bytes=b"dummy_voice"
        )

        if session_created:
            mock_worker_session.rollback.assert_called()
            assert mock_worker_session.__aexit__.called
        else:
            mock_worker_session.__aenter__.assert_not_called()
            mock_worker_session.rollback.assert_not_called()

        assert mock_openai_call.call_count == 4
        assert result.failed()


def test_process_expense_task_garbage_audio_sends_joke_and_no_db_write(
    test_session_for_pipeline, mock_bot
):

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

    mock_ai_response = ReceiptListAnalysisSchema(
        is_shopping_related=False,
        error_message="Красиво поёшь! Но где тут траты? Давай ближе к делу.",
        transactions=[],
    )

    joke_message = "Красиво поёшь! Но где тут траты? Давай ближе к делу."
    mock_bot.close = AsyncMock()

    with patch(
        "services.utils_pipelines.get_isolated_session",
        return_value=test_session_for_pipeline,
    ), patch(
        "services.client.ai_service.process_voice_message",
        new_callable=AsyncMock,
        return_value=mock_ai_response,
    ), patch(
        "aiogram.client.session.aiohttp.AiohttpSession.close", new_callable=AsyncMock
    ), patch(
        "services.pipelines.save_receipt_to_db", new_callable=AsyncMock
    ) as mock_save_db, patch(
        "services.pipelines.Bot", return_value=mock_bot
    ):

        result = process_expense_task.delay(
            chat_id=12345,
            db_user_id=42,
            locale="ru",
            voice_bytes=b"garbage_audio_bytes",
        )

        assert result.successful()

        mock_bot.send_message.assert_awaited_once_with(
            chat_id=12345, text=f"❌ {joke_message}"
        )

        mock_save_db.assert_not_called()


async def test_delete_check_idempotency_on_double_click(
    test_session_for_pipeline, user_for_pipeline, data_transaction_ai
):

    test_batch_id = str(uuid.uuid4())

    await save_receipt_to_db(
        session=test_session_for_pipeline,
        user_id=user_for_pipeline.id,
        analysis_result=data_transaction_ai,
        photo_url="http://fake.url",
        raw_text=data_transaction_ai.model_dump_json(),
        batch_id=test_batch_id,
    )

    tx_count_before = await test_session_for_pipeline.scalar(
        select(func.count())
        .select_from(Transactions)
        .where(Transactions.batch_id == test_batch_id)
    )
    assert tx_count_before == 1, "The test transaction was not saved to the database!"

    first_click = await delete_check(
        batch_id=test_batch_id, session=test_session_for_pipeline
    )

    assert first_click is True, "The first call to delete_check must return True."

    tx_exists = await test_session_for_pipeline.scalar(
        select(Transactions).where(Transactions.batch_id == test_batch_id)
    )
    assert (
        tx_exists is None
    ), "The transaction remained in the Transactions table after deletion!"

    items_count = await test_session_for_pipeline.scalar(
        select(func.count())
        .select_from(TransactionItems)
        .where(TransactionItems.category == "food")
    )
    assert (
        items_count == 0
    ), "The receipt items (TransactionItems) were not deleted from the database!"

    second_click = await delete_check(
        batch_id=test_batch_id, session=test_session_for_pipeline
    )

    assert (
        second_click is False
    ), "The second call to delete_check should return False (already deleted)."


def test_merge_transactions_by_category_logic(data_for_merge_by_cat):

    processed_data = merge_transactions_by_category(data_for_merge_by_cat)

    assert len(processed_data.transactions) == 2

    food_tx = next(t for t in processed_data.transactions if t.category == "food")
    transport_tx = next(
        t for t in processed_data.transactions if t.category == "transport"
    )

    assert (
        food_tx.amount == 200.0
    ), "The total expenditure for the 'food' category has been aggregated incorrectly."
    assert transport_tx.amount == 300.0

    assert (
        food_tx.description == "Супермаркет, Рынок"
    ), "The category descriptions did not merge correctly."

    # Проверка Товаров: Массивы items должны объединиться
    assert (
        len(food_tx.items) == 2
    ), "Items from different receipts were not combined into a single category"
    names = [item.name for item in food_tx.items]
    assert "Молоко" in names
    assert "Хлеб" in names
