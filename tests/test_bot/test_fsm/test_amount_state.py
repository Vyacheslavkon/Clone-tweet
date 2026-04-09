import pytest
from aiogram.types import Message, Chat, User
from datetime import datetime
from sqlalchemy import select
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from financial_bot.models import Transactions  # Ваша модель SQLAlchemy

from financial_bot.handlers.transactions import (go_back, process_amount_input,
                                                 type_amount, category_amount,
                                                 end_with_message,end_with_callback,
                                                 save_to_db_and_finish)
from financial_bot.models import Transactions
from aiogram.types import Update


@pytest.mark.asyncio
async def test_full_transaction_flow(test_dp, mock_bot, create_mock_message, create_mock_callback, test_session):
    user_id = 12345

    # --- ШАГ 1: Ввод суммы (Message) ---
    # Фабрика создает мок, диспетчер видит текст "500"
    msg_step1 = create_mock_message(text="500", user_id=user_id)
    await test_dp.feed_update(mock_bot, Update(message=msg_step1, update_id=1))

    # Проверяем, что бот ответил и перевел состояние (необязательно, но полезно)
    msg_step1.answer.assert_called()
    # В Redis уже лежит сумма 500

    # --- ШАГ 2: Выбор типа "Расход" (Callback Query) ---
    # Используем фабрику для колбэка. data="expense" — это то, что зашито в Inline кнопке
    cb_step2 = create_mock_callback(data="type_expense", user_id=user_id)
    await test_dp.feed_update(mock_bot, Update(callback_query=cb_step2, update_id=2))

    # --- ШАГ 3: Выбор категории (Callback Query) ---
    cb_step3 = create_mock_callback(data="cat_food", user_id=user_id)
    await test_dp.feed_update(mock_bot, Update(callback_query=cb_step3, update_id=3))

    # --- ШАГ 4: Ввод описания и финал (Message) ---
    msg_step4 = create_mock_message(text="Обед в кафе", user_id=user_id)
    await test_dp.feed_update(mock_bot, Update(message=msg_step4, update_id=4))

    # --- ИТОГОВАЯ ПРОВЕРКА В БАЗЕ ---
    # Здесь мы проверяем результат работы всей цепочки



    result = await test_session.execute(select(Transactions).filter_by(tg_id=user_id))
    record = result.scalar_one()

    assert record.amount == 500
    assert record.type == "expense"
    assert record.category == "food"
    assert record.comment == "Обед в кафе"
