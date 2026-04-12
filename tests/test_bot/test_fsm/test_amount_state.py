import pytest
from sqlalchemy import select
from financial_bot.states.amount_states import AmountState
from financial_bot.models import Transactions


def called_bot(mock_bot, text: str) -> bool:
    # assert any(
    #     "SendMessage" or "EditMessageText" in str(call) and text in str(call)
    #     for call in mock_bot.mock_calls
    # )

    assert any(
        any(m in str(call) for m in ["SendMessage", "EditMessageText"])
        and text in str(call)
        for call in mock_bot.mock_calls
    ), f"Текст '{text}'not found in bot responses."

@pytest.mark.asyncio
async def test_full_transaction_flow(test_dp, mock_bot, create_mock_update, test_session, test_i18n, test_user):



    create_message, create_callback = create_mock_update
    user_id = 12345

    with test_i18n.context():

        state = test_dp.fsm.get_context(bot=mock_bot, user_id=user_id, chat_id=user_id)
        await state.set_state(AmountState.waiting_for_amount)

        msg_step1 = create_message(text="500", user_id=user_id, update_id=1)
        await test_dp.feed_update(mock_bot, msg_step1)

        #print(mock_bot.mock_calls)

        called_bot(mock_bot, "Выберите тип")
        mock_bot.reset_mock()

        cb_step2 = create_callback(data="type_expense", user_id=user_id,  update_id=2)
        await test_dp.feed_update(mock_bot, cb_step2)

        called_bot(mock_bot,"Выберите категорию")
        mock_bot.reset_mock()

        cb_step3 = create_callback(data="cat_food", user_id=user_id,  update_id=3)
        await test_dp.feed_raw_update(mock_bot, cb_step3)

        called_bot(mock_bot, "Напишите комментарий")
        mock_bot.reset_mock()

        msg_step4 = create_message(text="Обед в кафе", user_id=user_id,  update_id=4)
        await test_dp.feed_raw_update(mock_bot, msg_step4)

        called_bot(mock_bot, "Данные успешно сохранены!")
        result = await test_session.execute(select(Transactions))

        record = result.scalar_one()
        assert record.amount == 500
        assert record.type == "expense"
        assert record.category == "food"
        assert record.description == "Обед в кафе"


