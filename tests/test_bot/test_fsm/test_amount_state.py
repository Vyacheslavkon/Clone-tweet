import pytest
from aiogram.types import Message, Chat, User
from datetime import datetime

from aiogram_i18n import I18nContext
from sqlalchemy import select
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from financial_bot.models import Transactions
from financial_bot.states.amount_states import AmountState

from financial_bot.models import Transactions
from aiogram.types import Update


@pytest.mark.asyncio
async def test_full_transaction_flow(test_dp, mock_bot, create_mock_update, test_session, test_i18n):



    create_message, create_callback = create_mock_update
    user_id = 12345

    with test_i18n.context():

        state = test_dp.fsm.get_context(bot=mock_bot, user_id=user_id, chat_id=user_id)
        await state.set_state(AmountState.waiting_for_amount)



        msg_step1 = create_message(text="500", user_id=user_id,  update_id=1)
        update = Update(**msg_step1)
        await test_dp.feed_update(mock_bot, update)

        mock_bot.send_message.assert_called()


        cb_step2 = create_callback(data="type_expense", user_id=user_id,  update_id=2)
        await test_dp.feed_raw_update(mock_bot, cb_step2)

        cb_step3 = create_callback(data="cat_food", user_id=user_id,  update_id=3)
        await test_dp.feed_raw_update(mock_bot, cb_step3)

        msg_step4 = create_message(text="Обед в кафе", user_id=user_id,  update_id=4)
        await test_dp.feed_raw_update(mock_bot, msg_step4)

        result = await test_session.execute(select(Transactions).filter_by(tg_id=user_id))
        record = result.scalar_one()

        assert record.amount == 500
        assert record.type == "expense"
        assert record.category == "food"
        assert record.comment == "Обед в кафе"
    # finally:
    #     I18nContext.reset_current(token)



    # state = test_dp.fsm.get_context(bot=mock_bot, user_id=user_id, chat_id=user_id)
    # await state.set_state(AmountState.waiting_for_amount)
    #
    # msg_step1 = create_message(text="500", user_id=user_id, update_id=1)
    # await test_dp.feed_raw_update(mock_bot, msg_step1)
    #
    # mock_bot.send_message.assert_called()
    #
    #
    # # --- ШАГ 2: Выбор типа "Расход" (Callback Query) ---
    # # Используем фабрику для колбэка. data="expense" — это то, что зашито в Inline кнопке
    # cb_step2 = create_callback(data="type_expense", user_id=user_id, update_id=2)
    # await test_dp.feed_raw_update(mock_bot, cb_step2)
    #
    #
    # cb_step3 = create_callback(data="cat_food", user_id=user_id, update_id=3)
    # await test_dp.feed_raw_update(mock_bot, cb_step3)
    #
    #
    # msg_step4 = create_message(text="Обед в кафе", user_id=user_id, update_id=4)
    # await test_dp.feed_raw_update(mock_bot, msg_step4)
    #
    #
    # result = await test_session.execute(select(Transactions).filter_by(tg_id=user_id))
    # record = result.scalar_one()
    #
    # assert record.amount == 500
    # assert record.type == "expense"
    # assert record.category == "food"
    # assert record.comment == "Обед в кафе"
