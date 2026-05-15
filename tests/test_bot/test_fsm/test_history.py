import pytest

from financial_bot.states.history_states import HistoryState
from financial_bot.repositories import get_report_period, get_planned_goals
from financial_bot.handlers.utils import (formatters,
                                          get_month_boundaries,
                                          get_month_name,
                                          format_multi_report)
from tests.test_bot.utils import get_expected_timestamps
from tests.test_bot.utils import (
    called_bot,
    keyboard_check,
    kb_history,
    get_week_boundaries
)


async def test_report_history(test_dp, mock_bot, create_mock_update, test_user, test_i18n):

    create_message, _ = create_mock_update
    user_id = test_user.id

    create_message, _ = create_mock_update

    text = test_i18n.gettext("History")
    message = create_message(text=text, user_id=user_id, update_id=1)
    await test_dp.feed_update(mock_bot, message)
    expected_text = test_i18n.gettext("Please, select period")
    called_bot(mock_bot, expected_text)

    buttons = kb_history()

    keyboard_check(buttons, mock_bot, test_i18n)

    state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)
    current_state = await state.get_state()
    assert current_state == HistoryState.waiting_for_period_history


async def test_history_two_week(test_dp, test_session, test_i18n,
                                mock_bot, create_mock_update,
                                test_user, test_data, test_transaction):

    mock_bot.id = 12345678
    test_dp["bot"] = mock_bot

    _, callback_message = create_mock_update

    state = test_dp.fsm.get_context(bot=mock_bot, user_id=test_user.tg_id, chat_id=test_user.tg_id)
    await state.set_state(HistoryState.waiting_for_period_history)

    message = callback_message(data="two_week", user_id=test_user.tg_id, update_id=1)

    with test_i18n.context():
        await test_dp.feed_update(mock_bot, message)

        cur_week = "current week"
        last_week = "last week"
        start_cur_week, end_cur_week = get_week_boundaries()
        start_prev_week, end_prev_week = get_week_boundaries(last_week)

        data_cur_week = await get_report_period(test_session, test_user.tg_id,
                                          start_cur_week, end_cur_week)

        data_last_week = await get_report_period(test_session, test_user.tg_id,
                                           start_prev_week, end_prev_week)


        expected_data = format_multi_report([
                        {"data": data_cur_week, "period_name": cur_week},
                        {"data": data_last_week, "period_name": last_week}
                         ])

        mock_bot.send_message.assert_called_once()
        _, kwargs = mock_bot.send_message.call_args

        assert kwargs["text"] == expected_data
        assert kwargs["chat_id"] == test_user.tg_id
        assert kwargs["message_id"] == 2
