import os
import uuid
from unittest.mock import AsyncMock, patch
import uuid as uuid_module
import openai
import pytest
from celery.exceptions import Retry
from sqlalchemy import func, select

from financial_bot.models import TransactionItems, Transactions
from financial_bot.repositories import delete_check, save_receipt_to_db
from financial_bot.tasks.ai import process_expense_task
from services.celery_app import app as celery_app
from services.pipelines import async_process_receipt
from services.schemas import (
    ReceiptListAnalysisSchema, ReceiptItemSchema, ReceiptAnalysisSchema
)
from services.utils_pipelines import merge_transactions_by_category

CHAT_ID = 12345
DB_USER_ID = 42
STATUS_MESSAGE_ID = 999


async def test_process_expense_task_writes_to_real_db(
    mock_ai_service,
    mock_bot,
    test_session_for_pipeline,
    user_for_pipeline,
    fake_analysis,
        audio_file
):
    user_id = user_for_pipeline.id
    chat_id = 11111

    mock_ai_service.return_value = fake_analysis

    with patch(
            "services.pipelines.get_isolated_session",
            return_value=test_session_for_pipeline,
    ), patch(
        "services.pipelines.get_shared_bot", return_value=mock_bot
    ), patch(
        "services.pipelines.Redis.from_url"
    ) as mock_redis_from_url, patch(
            "services.pipelines.FinancialCacheService.invalidate_user_cache",
            new_callable=AsyncMock,
        ) as mock_invalidate:
        mock_redis_from_url.return_value.__aenter__.return_value = AsyncMock()

        await async_process_receipt(
            chat_id=chat_id,
            db_user_id=user_id,
            locale="ru",
            voice_file_path=audio_file,
            status_message_id=STATUS_MESSAGE_ID
        )

    stmt = select(Transactions).where(Transactions.user_id == user_id)
    result = await test_session_for_pipeline.execute(stmt)
    db_transactions = result.scalars().all()

    assert len(db_transactions) == 1
    assert db_transactions[0].amount == 250.0
    assert db_transactions[0].category == "food"
    assert uuid_module.UUID(db_transactions[0].batch_id)

    mock_invalidate.assert_awaited_once_with(user_id=user_id)
    mock_bot.edit_message_text.assert_awaited_once()
    call_kwargs = mock_bot.edit_message_text.call_args.kwargs
    assert call_kwargs["chat_id"] == chat_id
    assert call_kwargs["message_id"] == STATUS_MESSAGE_ID
    assert "250" in call_kwargs["text"]
    assert call_kwargs["reply_markup"] is not None



# to pay attention to. it makes sense?
def test_process_expense_task_success(mock_proc_receipt, audio_file, celery_eager):

    expected_output = {"status": "success", "extracted_amount": 500.0}

    mock_proc_receipt.return_value = expected_output

    result = process_expense_task.delay(
        chat_id=CHAT_ID,
        db_user_id=DB_USER_ID,
        locale="ru",
        voice_file_path=audio_file,
        status_message_id=STATUS_MESSAGE_ID,
    )

    assert result.successful()
    assert result.result == expected_output
   # mock_proc_receipt.assert_called_once_with()


@pytest.mark.parametrize("celery_eager", [False], indirect=True)
def test_process_expense_task_fails_after_exhausting_retries_on_openai_error(mock_bot,
                                                                             mock_proc_receipt,
                                                                             audio_file,
                                                                             celery_eager,
                                                                             mock_pipeline_infra):

    mock_proc_receipt.side_effect = openai.OpenAIError("Rate limit exceeded")

    result = process_expense_task.delay(
        chat_id=CHAT_ID,
        db_user_id=DB_USER_ID,
        locale="ru",
        voice_file_path=audio_file,
        status_message_id=STATUS_MESSAGE_ID,

    )

    assert mock_proc_receipt.call_count == process_expense_task.max_retries + 1
    assert isinstance(result.result, openai.OpenAIError)
    assert result.failed()
    assert not os.path.exists(audio_file)
    mock_bot.edit_message_text.assert_awaited_once()
    _, kwargs = mock_bot.edit_message_text.call_args
    assert kwargs["chat_id"] == CHAT_ID
    assert kwargs["message_id"] == STATUS_MESSAGE_ID


def test_task_keeps_file_between_retry_attempts(mock_proc_receipt, audio_file, celery_eager):
    """Проверяем ОДНУ попытку с ретраем — файл не должен удаляться раньше времени."""
    mock_proc_receipt.side_effect = openai.OpenAIError("Rate limit exceeded")

    with pytest.raises(Retry):
        process_expense_task.apply(
            args=(CHAT_ID, DB_USER_ID, "ru", audio_file, STATUS_MESSAGE_ID),
            throw=True,
        )

    assert os.path.exists(audio_file)  # файл должен сохраниться для повторной попытки


def test_process_expense_task_network_error_rolls_back_db(
    celery_eager,
        mock_isolated_session,
        mock_voice_processing,
        mock_pipeline_infra,
        audio_file,
        mock_bot
):

    mock_worker_session = AsyncMock()
    mock_isolated_session.return_value = mock_worker_session
    mock_voice_processing.side_effect = openai.APITimeoutError("Request timed out")

    with pytest.raises(Retry):
        process_expense_task.delay(
            chat_id=CHAT_ID,
            db_user_id=DB_USER_ID,
            locale="ru",
            voice_file_path=audio_file,
            status_message_id=STATUS_MESSAGE_ID,
        )

    mock_isolated_session.assert_called_once()
    mock_worker_session.rollback.assert_awaited_once()
    mock_worker_session.close.assert_awaited_once()
    mock_voice_processing.assert_awaited_once()

    mock_bot.edit_message_text.assert_not_awaited()
    mock_bot.send_message.assert_not_awaited()


def test_process_expense_task_garbage_audio_sends_joke_and_no_db_write(
    test_session_for_pipeline,
        mock_bot,
        celery_eager,
        audio_file,
        mock_isolated_session,
        mock_voice_processing,
        mock_pipeline_infra,
        mock_save_receipt
):
    mock_isolated_session.return_value = AsyncMock()
    mock_voice_processing.return_value = ReceiptListAnalysisSchema(
        is_shopping_related=False,
        error_message="You sing a fine tune! But where are the expenses?",
        transactions=[],
    )

    result = process_expense_task.delay(
        chat_id=CHAT_ID,
        db_user_id=DB_USER_ID,
        locale="ru",
        voice_file_path=audio_file,
        status_message_id=STATUS_MESSAGE_ID,
    )

    assert result.successful()
    mock_bot.edit_message_text.assert_awaited_once()

    _, kwargs = mock_bot.edit_message_text.call_args
    assert kwargs["chat_id"] == CHAT_ID
    assert kwargs["message_id"] == STATUS_MESSAGE_ID
    assert kwargs["text"] == f"❌ {mock_voice_processing.return_value.error_message}"

    mock_save_receipt.assert_not_awaited()


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


def test_all_amounts_non_positive_reports_no_transactions(
    celery_eager, audio_file, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_voice_processing, mock_save_receipt,
):
    mock_isolated_session.return_value = AsyncMock()
    mock_voice_processing.return_value = ReceiptListAnalysisSchema(
        is_shopping_related=True,
        error_message=None,
        transactions=[
            ReceiptAnalysisSchema(
                amount=0,
                category="food",
                items=[
                    ReceiptItemSchema(name="Milk", price=0),
                    ReceiptItemSchema(name="Water", price=-0)
                ],
                type="expense"
            )

        ],
    )

    result = process_expense_task.delay(
        chat_id=CHAT_ID,
        db_user_id=DB_USER_ID,
        locale="",
        voice_file_path=audio_file,
        status_message_id=STATUS_MESSAGE_ID,
    )

    assert result.successful()
    mock_save_receipt.assert_not_awaited()

    _, kwargs = mock_bot.edit_message_text.call_args
    assert "No transactions found" in kwargs["text"]


def test_missing_audio_file_rolls_back_gracefully(
    celery_eager, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_voice_processing,
):
    session = AsyncMock()
    mock_isolated_session.return_value = session

    result = process_expense_task.delay(
        chat_id=CHAT_ID, db_user_id=DB_USER_ID, locale="ru",
        voice_file_path="/nonexistent/path.ogg", status_message_id=STATUS_MESSAGE_ID,
    )

    assert result.successful()
    session.rollback.assert_awaited_once()
    session.close.assert_awaited_once()
    # До вызова AI дело не должно было дойти
    mock_voice_processing.assert_not_awaited()



def test_successful_save_survives_cache_invalidation_failure(
    celery_eager, audio_file, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_voice_processing, mock_save_receipt,
    mock_redis_cache,
):
    session = AsyncMock()
    mock_isolated_session.return_value = session
    mock_voice_processing.return_value = ReceiptListAnalysisSchema(
        is_shopping_related=True,
        error_message=None,
        transactions=[ReceiptAnalysisSchema(
                amount=15.5,
                category="food",
                items=[
                    ReceiptItemSchema(name="Milk", price=5),
                    ReceiptItemSchema(name="Water", price=-10)
                ],
                type="expense"
            )],
    )
    mock_redis_cache.side_effect = ConnectionError("redis down")

    result = process_expense_task.delay(
        chat_id=CHAT_ID,
        db_user_id=DB_USER_ID,
        locale="ru",
        voice_file_path=audio_file,
        status_message_id=STATUS_MESSAGE_ID,
    )

    assert result.successful()
    mock_save_receipt.assert_awaited_once()
    session.rollback.assert_not_awaited()
    session.close.assert_awaited_once()


    mock_bot.edit_message_text.assert_awaited_once()


def test_unexpected_error_rolls_back_and_shows_generic_message(
    celery_eager, audio_file, mock_bot, mock_pipeline_infra,
    mock_isolated_session, mock_voice_processing,
):
    session = AsyncMock()
    mock_isolated_session.return_value = session
    mock_voice_processing.side_effect = ValueError("unexpected schema mismatch")

    result = process_expense_task.delay(
        chat_id=CHAT_ID, db_user_id=DB_USER_ID, locale="ru",
        voice_file_path=audio_file, status_message_id=STATUS_MESSAGE_ID,
    )

    # В отличие от network error, тут задача завершается успешно (без re-raise)
    assert result.successful()

    session.rollback.assert_awaited_once()
    session.close.assert_awaited_once()

    mock_bot.edit_message_text.assert_awaited_once()
    _, kwargs = mock_bot.edit_message_text.call_args
    assert "couldn't recognize your receipt" in kwargs["text"]