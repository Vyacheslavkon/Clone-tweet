from financial_bot.repositories import (
    add_data_for_user,
    get_limit_expense,
    get_monthly_budget,
    get_saved_goal,
)
from financial_bot.schemas import AddData
from financial_bot.states.add_data_states import AddDataState
from tests.test_bot.utils import (
    called_bot,
    comparison_dict,
    dict_invalid_data,
    keyboard_check,
    keyboards,
)

main_menu, buttons = keyboards()


async def test_adding_value_budget(
    test_dp, test_session, test_user, mock_bot, create_mock_update, test_i18n
):

    create_message, _ = create_mock_update
    user_id = 12345

    state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)
    await state.set_state(AddDataState.waiting_for_type_data)

    text = test_i18n.gettext("Add/change data")
    msg_first = create_message(text=text, user_id=user_id, update_id=1)
    await test_dp.feed_update(mock_bot, msg_first)

    expected_text = test_i18n.gettext("Please, select data type")
    called_bot(mock_bot, expected_text)

    keyboard_check(buttons, mock_bot, test_i18n)

    text = test_i18n.gettext("monthly budget")
    msg_first = create_message(text=text, user_id=user_id, update_id=2)
    await test_dp.feed_update(mock_bot, msg_first)

    expected_text = test_i18n.gettext("Enter your estimated monthly budget")
    called_bot(mock_bot, expected_text)

    await state.set_state(AddDataState.waiting_for_monthly_budget)
    msg_second = create_message(text="1000", user_id=user_id, update_id=3)

    await test_dp.feed_update(mock_bot, msg_second)

    expected_text_end = test_i18n.gettext("The data was saved successfully.")
    called_bot(mock_bot, expected_text_end)

    keyboard_check(main_menu, mock_bot, test_i18n)

    budget = await get_monthly_budget(test_session, test_user.tg_id)

    assert budget == 1000


async def test_change_value_budget(
    test_dp, test_session, test_user, budget, mock_bot, create_mock_update, test_i18n
):

    create_message, _ = create_mock_update
    user_id = 12345

    state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)
    await state.set_state(AddDataState.waiting_for_type_data)

    text = test_i18n.gettext("monthly budget")
    msg_first = create_message(text=text, user_id=user_id, update_id=1)
    await test_dp.feed_update(mock_bot, msg_first)

    expected_text = test_i18n.gettext("Enter your estimated monthly budget")
    called_bot(mock_bot, expected_text)

    await state.set_state(AddDataState.waiting_for_monthly_budget)
    msg_second = create_message(text="1000", user_id=user_id, update_id=2)

    await test_dp.feed_update(mock_bot, msg_second)

    expected_text_lim_exp = test_i18n.gettext("Enter the spending limit amount")
    called_bot(mock_bot, expected_text_lim_exp)

    await state.set_state(AddDataState.waiting_for_limit_expense)

    msg_third = create_message(text="500", user_id=user_id, update_id=3)
    await test_dp.feed_update(mock_bot, msg_third)

    expected_text_end = test_i18n.gettext("The data was saved successfully.")
    called_bot(mock_bot, expected_text_end)

    budget = await get_monthly_budget(test_session, test_user.tg_id)
    expected_limit = 500 / budget * 100
    limit_expense = await get_limit_expense(test_session, test_user.tg_id)
    assert budget == 1000
    assert limit_expense == expected_limit


async def test_invalid_value_budget(
    test_dp, test_user, test_i18n, create_mock_update, mock_bot
):
    create_message, _ = create_mock_update
    user_id = 12345

    state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)
    await state.set_state(AddDataState.waiting_for_type_data)

    text = test_i18n.gettext("monthly budget")
    msg_first = create_message(text=text, user_id=user_id, update_id=1)
    await test_dp.feed_update(mock_bot, msg_first)

    expected_text = test_i18n.gettext("Enter your estimated monthly budget")

    called_bot(mock_bot, expected_text)

    await state.set_state(AddDataState.waiting_for_monthly_budget)
    update_id = 1
    for text, key in dict_invalid_data.items():
        msg = create_message(text=text, user_id=user_id, update_id=update_id)

        await test_dp.feed_update(mock_bot, msg)

        expected_data = test_i18n.gettext(key)
        called_bot(mock_bot, expected_data)

        keyboard_check(buttons, mock_bot, test_i18n)

        update_id += 1


async def test_adding_limit_expense(
    mock_bot, test_session, test_user, test_i18n, test_dp, create_mock_update, budget
):
    create_message, _ = create_mock_update
    user_id = 12345

    state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)
    await state.set_state(AddDataState.waiting_for_type_data)

    text = test_i18n.gettext("limit expense")
    msg_first = create_message(text=text, user_id=user_id, update_id=1)
    await test_dp.feed_update(mock_bot, msg_first)

    expected_text = test_i18n.gettext("Enter the spending limit amount")
    called_bot(mock_bot, expected_text)

    await state.set_state(AddDataState.waiting_for_limit_expense)
    msg_second = create_message(text="1000", user_id=user_id, update_id=1)

    await test_dp.feed_update(mock_bot, msg_second)

    expected_data = test_i18n.gettext("The data was saved successfully.")
    called_bot(mock_bot, expected_data)

    keyboard_check(main_menu, mock_bot, test_i18n)

    expected_limit = 1000 / budget.monthly_budget * 100
    limit_expense = await get_limit_expense(test_session, test_user.tg_id)

    assert limit_expense == expected_limit


async def test_add_limit_expense_no_budget(
    mock_bot, test_user, test_i18n, test_dp, create_mock_update
):

    create_message, _ = create_mock_update
    user_id = 12345

    state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)
    await state.set_state(AddDataState.waiting_for_type_data)

    text = test_i18n.gettext("limit expense")
    msg_first = create_message(text=text, user_id=user_id, update_id=1)
    await test_dp.feed_update(mock_bot, msg_first)

    expected_text = test_i18n.gettext("Please set a monthly budget first.")
    called_bot(mock_bot, expected_text)


async def test_invalid_value_limit_expense(
    mock_bot, test_dp, test_user, test_session, create_mock_update, test_i18n, budget
):

    create_message, _ = create_mock_update
    user_id = 12345

    state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)

    await state.set_state(AddDataState.waiting_for_limit_expense)

    update_id = 1

    for text, key in comparison_dict.items():
        # mock_bot.send_message.reset_mock()
        msg = create_message(text=text, user_id=user_id, update_id=update_id)

        await test_dp.feed_update(mock_bot, msg)

        expected_text = test_i18n.gettext(key)
        called_bot(mock_bot, expected_text)

        keyboard_check(buttons, mock_bot, test_i18n)

        update_id += 1


async def test_limit_expense_zero_or_no_budget(
    mock_bot, test_dp, test_user, test_session, create_mock_update, test_i18n
):

    create_message, _ = create_mock_update
    user_id = 12345

    state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)
    await state.set_state(AddDataState.waiting_for_limit_expense)

    msg = create_message(text="100", user_id=user_id, update_id=1)

    await test_dp.feed_update(mock_bot, msg)

    expected_text = test_i18n.gettext(
        "You don't have a budget set! Set a basic budget first."
    )
    called_bot(mock_bot, expected_text)

    budget = AddData(monthly_budget=0)

    await add_data_for_user(test_session, budget, test_user.tg_id)

    msg = create_message(text="100", user_id=user_id, update_id=1)

    await test_dp.feed_update(mock_bot, msg)

    called_bot(mock_bot, expected_text)

    zero_budget = await get_monthly_budget(test_session, test_user.tg_id)

    assert zero_budget == 0


async def test_saved_goal(
    mock_bot, test_dp, test_i18n, budget, test_user, test_session, create_mock_update
):

    create_message, _ = create_mock_update
    user_id = 12345

    state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)
    await state.set_state(AddDataState.waiting_for_type_data)

    text = test_i18n.gettext("savings goal")
    msg_first = create_message(text=text, user_id=user_id, update_id=1)
    await test_dp.feed_update(mock_bot, msg_first)

    expected_text = test_i18n.gettext("Enter your desired savings amount")
    called_bot(mock_bot, expected_text)

    await state.set_state(AddDataState.waiting_for_savings_goal)

    msg_second = create_message(text="300", user_id=user_id, update_id=1)
    await test_dp.feed_update(mock_bot, msg_second)

    expected_data = test_i18n.gettext("The data was saved successfully.")
    called_bot(mock_bot, expected_data)

    keyboard_check(main_menu, mock_bot, test_i18n)

    saved_goal = await get_saved_goal(test_session, test_user.tg_id)

    assert saved_goal == 300


async def test_saved_goal_no_budget(
    mock_bot, test_dp, test_i18n, test_user, test_session, create_mock_update
):

    create_message, _ = create_mock_update
    user_id = 12345

    state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)
    await state.set_state(AddDataState.waiting_for_type_data)

    text = test_i18n.gettext("savings goal")
    msg_first = create_message(text=text, user_id=user_id, update_id=1)
    await test_dp.feed_update(mock_bot, msg_first)

    expected_text = test_i18n.gettext("Please set a monthly budget first.")
    called_bot(mock_bot, expected_text)


async def test_saving_goal_zero_or_no_budget(
    mock_bot, test_dp, test_user, test_session, create_mock_update, test_i18n
):

    create_message, _ = create_mock_update
    user_id = 12345

    state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)
    await state.set_state(AddDataState.waiting_for_savings_goal)

    text = "100"
    msg = create_message(text=text, user_id=user_id, update_id=1)

    await test_dp.feed_update(mock_bot, msg)

    expected_text = test_i18n.gettext(
        "You don't have a budget set! Set a basic budget first."
    )
    called_bot(mock_bot, expected_text)

    budget = AddData(monthly_budget=0)

    await add_data_for_user(test_session, budget, test_user.tg_id)

    await test_dp.feed_update(mock_bot, msg)

    called_bot(mock_bot, expected_text)

    zero_budget = await get_monthly_budget(test_session, test_user.tg_id)

    assert zero_budget == 0


async def test_invalid_value_saving_goal(
    mock_bot, test_dp, test_user, test_session, create_mock_update, test_i18n, budget
):
    create_message, _ = create_mock_update
    user_id = 12345

    state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)

    await state.set_state(AddDataState.waiting_for_savings_goal)

    update_id = 1

    for text, key in comparison_dict.items():
        mock_bot.send_message.reset_mock()
        msg = create_message(text=text, user_id=user_id, update_id=update_id)

        await test_dp.feed_update(mock_bot, msg)

        expected_text = test_i18n.gettext(key)
        called_bot(mock_bot, expected_text)

        keyboard_check(buttons, mock_bot, test_i18n)

        update_id += 1
