import pytest
from sqlalchemy.exc import IntegrityError

from financial_bot.models import Transactions, TransactionItems


async def test_transaction_amount_must_be_positive(test_session_for_pipeline, user_for_pipeline):
    bad_transaction = Transactions(
        user_id=user_for_pipeline.id,
        amount=-100,
        category="food",
        type="expense",
        batch_id="test-batch-1",
    )
    test_session_for_pipeline.add(bad_transaction)

    with pytest.raises(IntegrityError, match="ck_transactions_amount_positive"):
        await test_session_for_pipeline.flush()



    await test_session_for_pipeline.rollback()



async def test_transaction_amount_zero_is_rejected(test_session_for_pipeline, user_for_pipeline):
    bad_transaction = Transactions(
        user_id=user_for_pipeline.id,
        amount=0,
        category="food",
        type="expense",
        batch_id="test-batch-2",
    )
    test_session_for_pipeline.add(bad_transaction)

    with pytest.raises(IntegrityError, match="ck_transactions_amount_positive"):
        await test_session_for_pipeline.flush()

    await test_session_for_pipeline.rollback()


async def test_transaction_item_price_cannot_be_negative(test_session_for_pipeline, user_for_pipeline):
    transaction = Transactions(
        user_id=user_for_pipeline.id,
        amount=500,
        category="food",
        type="expense",
        batch_id="test-batch-3",
    )
    test_session_for_pipeline.add(transaction)
    await test_session_for_pipeline.flush()

    bad_item = TransactionItems(
        transaction_id=transaction.id,
        name="Refund item",
        price=-50,  # нарушает constraint
        category="food",
    )
    test_session_for_pipeline.add(bad_item)

    with pytest.raises(IntegrityError, match="ck_transaction_items_price_positive"):
        await test_session_for_pipeline.flush()

    await test_session_for_pipeline.rollback()


async def test_transaction_item_price_zero_is_allowed(test_session_for_pipeline, user_for_pipeline):
    """price >= 0 (не строго >), значит ноль — валидное значение."""
    transaction = Transactions(
        user_id=user_for_pipeline.id,
        amount=500,
        category="food",
        type="expense",
        batch_id="test-batch-4",
    )
    test_session_for_pipeline.add(transaction)
    await test_session_for_pipeline.flush()

    free_item = TransactionItems(
        transaction_id=transaction.id,
        name="Free sample",
        price=0,
        category="food",
    )
    test_session_for_pipeline.add(free_item)

    await test_session_for_pipeline.flush()  # не должно упасть
    await test_session_for_pipeline.commit()

    assert free_item.id is not None