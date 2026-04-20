from sqlalchemy import select
from financial_bot.states.add_data_states import AddDataState
from financial_bot.models import UserBot
from tests.test_bot.utils import called_bot, add_data


async def test_add_data(test_dp, mock_bot, test_session, test_i18n, create_mock_update, test_user, budget):

    create_message, _ = create_mock_update
    user_id = 12345
    list_state = [AddDataState.waiting_for_monthly_budget,
                  AddDataState.waiting_for_limit_expense,
                  AddDataState.waiting_for_savings_goal]
    update_id = 1

    with test_i18n.context():

        state = test_dp.fsm.get_context(bot=mock_bot, user_id=user_id, chat_id=user_id)
        await state.set_state(AddDataState.waiting_for_type_data)
        update_id = 1
        num_state = 0
        for text, answer in add_data.items():
            msg = create_message(text=text, user_id=user_id, update_id=update_id)
            await test_dp.feed_update(mock_bot, msg)
            update_id += 1

            called_bot(mock_bot, answer)
            await state.set_state(list_state[num_state])
            msg_second = create_message(text="1000", user_id=user_id, update_id=update_id)
            await test_dp.feed_update(mock_bot, msg_second)
            called_bot(mock_bot, "Данные были успешно сохранены!")
            mock_bot.reset_mock()
            await state.set_state(AddDataState.waiting_for_type_data)
            num_state += 1