import json

import pytest
import openai
import uuid
import asyncio
from unittest.mock import MagicMock
from celery.exceptions import Retry
from sqlalchemy import select

from financial_bot.repositories import create_user
from financial_bot.schemas import CreateUser
from financial_bot.tasks.ai import process_expense_task
from services.schemas import ReceiptListAnalysisSchema, ReceiptAnalysisSchema, ReceiptItemSchema
from financial_bot.models import Transactions, UserBot
from services.pipelines import async_process_receipt


async def test_process_expense_task_writes_to_real_db(mock_ai_service, mock_bot,
                                                      test_session_for_pipeline
                                                      ):
    user_data = CreateUser(tg_id=12345, language_code="ru", first_name="TestUser")
    db_user = await create_user(test_session_for_pipeline, user_data)
    await test_session_for_pipeline.flush()

    user_id = db_user.id
    chat_id = 11111

    fake_item = ReceiptItemSchema(name="Кофе", price=250.0)
    fake_tx = ReceiptAnalysisSchema(
        amount=250.0,
        category="food",
        type="expense",
        description="кофейня",
        items=[fake_item]
    )
    fake_analysis = ReceiptListAnalysisSchema(
        is_shopping_related=True,
        transactions=[fake_tx],
        error_message=None
    )


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


#@pytest.mark.asyncio
# async def test_process_expense_task_openai_retry_logic(mock_ai_service, test_session):
#     """
#     Проверяем, что при сетевом сбое OpenAI таска инициирует
#     ретрай в Celery и делает ROLLBACK в базе (ничего не пишется).
#     """
#     mock_ai_service.process_voice_message.side_effect = openai.OpenAIError("Network timeout")
#
#     fake_self = MagicMock()
#     fake_self.request.retries = 1  # Допустим, это уже второй запуск
#     fake_self.retry.side_effect = Retry("Celery retry triggered")
#
#     with pytest.raises(Retry):
#         process_expense_task.delay(
#             #self=fake_self,
#             chat_id=123,
#             db_user_id=888,
#             locale="en",
#             voice_bytes=b"bytes"
#         )
#
#
#
#     # Убеждаемся, что в базу ничего не записалось для этого юзера
#     stmt = select(Transactions).where(Transactions.user_id == 888)
#     result = await test_session.execute(stmt)
#     assert len(result.scalars().all()) == 0
#
#
#     # Проверяем экспоненциальный countdown: 2 ** 1 = 2 секунды
#     fake_self.retry.assert_called_once()
#     assert fake_self.retry.call_args.kwargs["countdown"] == 2

