from sqlalchemy import select
from financial_bot.states.add_data_states import AddDataState
from financial_bot.models import UserBot
from tests.test_bot.utils import called_bot, dict_invalid_data, invalid_limit_expense
from financial_bot.repositories import get_monthly_budget, get_limit_expense, add_data_for_user
from financial_bot.schemas import AddData


# async def test_add_data(test_dp, mock_bot, test_session, test_i18n, create_mock_update, test_user, budget):
#
#     create_message, _ = create_mock_update
#     user_id = 12345
#     list_state = [AddDataState.waiting_for_monthly_budget,
#                   AddDataState.waiting_for_limit_expense,
#                   AddDataState.waiting_for_savings_goal]
#     update_id = 1
#
#     with test_i18n.context():
#
#         state = test_dp.fsm.get_context(bot=mock_bot, user_id=user_id, chat_id=user_id)
#         await state.set_state(AddDataState.waiting_for_type_data)
#         update_id = 1
#         num_state = 0
#         for text, answer in add_data.items():
#             msg = create_message(text=text, user_id=user_id, update_id=update_id)
#             await test_dp.feed_update(mock_bot, msg)
#             update_id += 1
#
#             called_bot(mock_bot, answer)
#             await state.set_state(list_state[num_state])
#             msg_second = create_message(text="1000", user_id=user_id, update_id=update_id)
#             await test_dp.feed_update(mock_bot, msg_second)
#             called_bot(mock_bot, "Данные были успешно сохранены!")
#             mock_bot.reset_mock()
#             await state.set_state(AddDataState.waiting_for_type_data)
#             num_state += 1


async def test_adding_value_budget(test_dp, test_session, test_user,
                                   mock_bot, create_mock_update, test_i18n):

    create_message, _ = create_mock_update
    user_id = 12345

    with test_i18n.context():

        state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)
        await state.set_state(AddDataState.waiting_for_type_data)

        msg_first = create_message(text="бюджет на месяц", user_id=user_id, update_id=1)
        await test_dp.feed_update(mock_bot, msg_first)

        called_bot(mock_bot, "Введите свой предполагаемый ежемесячный бюджет")

        await state.set_state(AddDataState.waiting_for_monthly_budget)
        msg_second = create_message(text="1000", user_id=user_id,update_id=1)

        await test_dp.feed_update(mock_bot, msg_second)

        called_bot(mock_bot, "Данные были успешно сохранены!")

        budget = await get_monthly_budget(test_session, test_user.tg_id)

        assert budget == 1000


async def test_change_value_budget(test_dp, test_session, test_user, budget,
                                   mock_bot, create_mock_update, test_i18n):

    create_message, _ = create_mock_update
    user_id = 12345

    with test_i18n.context():

        state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)
        await state.set_state(AddDataState.waiting_for_type_data)

        msg_first = create_message(text="бюджет на месяц", user_id=user_id, update_id=1)
        await test_dp.feed_update(mock_bot, msg_first)

        called_bot(mock_bot, "Введите свой предполагаемый ежемесячный бюджет")

        await state.set_state(AddDataState.waiting_for_monthly_budget)
        msg_second = create_message(text="1000", user_id=user_id,update_id=1)

        await test_dp.feed_update(mock_bot, msg_second)

        called_bot(mock_bot, "Введите сумму лимита расходов")

        await state.set_state(AddDataState.waiting_for_limit_expense)

        msg_third = create_message(text="500", user_id=user_id, update_id=1)
        await test_dp.feed_update(mock_bot, msg_third)

        called_bot(mock_bot, "Данные были успешно сохранены!")

        budget = await get_monthly_budget(test_session, test_user.tg_id)
        expected_limit = 500 / budget * 100
        limit_expense = await get_limit_expense(test_session, test_user.tg_id)
        assert budget == 1000
        assert limit_expense == expected_limit



async def test_invalid_value_budget(test_dp, test_user, test_i18n, create_mock_update, mock_bot):
    create_message, _ = create_mock_update
    user_id = 12345

    with test_i18n.context():
        state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)
        await state.set_state(AddDataState.waiting_for_type_data)

        msg_first = create_message(text="бюджет на месяц", user_id=user_id, update_id=1)
        await test_dp.feed_update(mock_bot, msg_first)

        called_bot(mock_bot, "Введите свой предполагаемый ежемесячный бюджет")

        await state.set_state(AddDataState.waiting_for_monthly_budget)

        for text, answer in dict_invalid_data.items():

            msg = create_message(text=text, user_id=user_id, update_id=1)

            await test_dp.feed_update(mock_bot, msg)

            called_bot(mock_bot, answer)



async def test_adding_limit_expense(mock_bot, test_session, test_user, test_i18n,
                             test_dp, create_mock_update, budget):
    create_message, _ = create_mock_update
    user_id = 12345

    with test_i18n.context():
        state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)
        await state.set_state(AddDataState.waiting_for_type_data)

        msg_first = create_message(text="лимит расходов", user_id=user_id, update_id=1)
        await test_dp.feed_update(mock_bot, msg_first)

        called_bot(mock_bot, "Введите сумму лимита расходов")

        await state.set_state(AddDataState.waiting_for_limit_expense)
        msg_second = create_message(text="1000", user_id=user_id, update_id=1)

        await test_dp.feed_update(mock_bot, msg_second)

        called_bot(mock_bot, "Данные были успешно сохранены!")

        expected_limit = 1000 / budget.monthly_budget * 100
        limit_expense = await get_limit_expense(test_session, test_user.tg_id)

        assert limit_expense == expected_limit


async def test_add_limit_expense_no_budget(mock_bot, test_user, test_i18n,
                                           test_dp, create_mock_update):

    create_message, _ = create_mock_update
    user_id = 12345

    with test_i18n.context():
        state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)
        await state.set_state(AddDataState.waiting_for_type_data)

        msg_first = create_message(text="лимит расходов", user_id=user_id, update_id=1)
        await test_dp.feed_update(mock_bot, msg_first)

        called_bot(mock_bot, "Пожалуйста, сначала установите ежемесячный бюджет")


async def test_invalid_value_limit_expense(mock_bot, test_dp, test_user, test_session,
                                           create_mock_update, test_i18n, budget):

    create_message, _ = create_mock_update
    user_id = 12345

    with test_i18n.context():
        state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)
        # await state.set_state(AddDataState.waiting_for_type_data)
        #
        # msg_first = create_message(text="лимит расходов", user_id=user_id, update_id=1)
        # await test_dp.feed_update(mock_bot, msg_first)
        #
        # called_bot(mock_bot, "Введите сумму лимита расходов")

        await state.set_state(AddDataState.waiting_for_limit_expense)

        for text, answer in invalid_limit_expense.items():

            msg = create_message(text=text, user_id=user_id, update_id=1)

            await test_dp.feed_update(mock_bot, msg)

            called_bot(mock_bot, answer)


async def test_limit_expense_zero_or_no_budget(mock_bot, test_dp, test_user, test_session,
                                           create_mock_update, test_i18n):

    create_message, _ = create_mock_update
    user_id = 12345

    with test_i18n.context():
        state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)
        await state.set_state(AddDataState.waiting_for_limit_expense)

        msg = create_message(text="100", user_id=user_id, update_id=1)

        await test_dp.feed_update(mock_bot, msg)

        called_bot(mock_bot,"**У вас нет установленного бюджета!**Сначала установите базовый бюджет.")

        budget = AddData(monthly_budget=0)

        await add_data_for_user(test_session, budget, test_user.tg_id)

        msg = create_message(text="100", user_id=user_id, update_id=1)

        await test_dp.feed_update(mock_bot, msg)

        called_bot(mock_bot, "**У вас нет установленного бюджета!**Сначала установите базовый бюджет.")

        zero_budget = await get_monthly_budget(test_session, test_user.tg_id)

        assert zero_budget == 0