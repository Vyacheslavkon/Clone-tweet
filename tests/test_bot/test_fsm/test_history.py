from datetime import datetime

from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
from unittest.mock import AsyncMock, patch

from financial_bot.states.history_states import HistoryState
from financial_bot.repositories import get_report_period
from financial_bot.handlers.utils import (formatters,
                                          format_multi_report,
                                          get_arbitrary_period)

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



async  def test_history_arbitrary_period(test_dp, test_session, mock_bot,
                              create_mock_update, test_user, test_i18n,
                              test_data, test_transaction):

    mock_bot.id = 12345678
    test_dp["bot"] = mock_bot

    _, callback_message = create_mock_update

    state = test_dp.fsm.get_context(bot=mock_bot, user_id=test_user.tg_id, chat_id=test_user.tg_id)
    await state.set_state(HistoryState.waiting_for_period_history)

    mock_start_date = datetime(2026, 5, 1)
    mock_end_date = datetime(2026, 5, 15)

    with test_i18n.context():

        update_step_1 = callback_message(data="period", user_id=test_user.tg_id, update_id=1)

        await test_dp.feed_update(mock_bot, update_step_1)

        mock_bot.send_message.assert_called_once()
        _, kwargs = mock_bot.send_message.call_args

        assert "start date" in kwargs["text"].lower()
        assert await state.get_state() == HistoryState.waiting_for_data_start.state
        mock_bot.reset_mock()

        start_callback_data = SimpleCalendarCallback(act="DAY", year=2026, month=5, day=1)
        update_step_2 = callback_message(
            data=start_callback_data.pack(), user_id=test_user.tg_id, update_id=2
        )


        with patch.object(SimpleCalendar, 'process_selection', new_callable=AsyncMock) as mock_select:

            mock_select.return_value = (True, mock_start_date)

            await test_dp.feed_update(mock_bot, update_step_2)


        mock_bot.edit_message_text.assert_called_once()
        mock_bot.edit_message_reply_markup.assert_called_once()


        fsm_data = await state.get_data()
        assert fsm_data["start_date"] == mock_start_date.isoformat()
        assert await state.get_state() == HistoryState.waiting_for_data_end.state
        mock_bot.reset_mock()


        end_callback_data = SimpleCalendarCallback(act="DAY", year=2026, month=5, day=15)
        update_step_3 = callback_message(
            data=end_callback_data.pack(), user_id=test_user.tg_id, update_id=3
        )

        with patch.object(SimpleCalendar, 'process_selection', new_callable=AsyncMock) as mock_select:
            mock_select.return_value = (True, mock_end_date)

            await test_dp.feed_update(mock_bot, update_step_3)


        mock_bot.send_message.assert_called_once()
        _, final_kwargs = mock_bot.send_message.call_args

        expected_start, expected_end = get_arbitrary_period(mock_start_date, mock_end_date)
        db_data = await get_report_period(test_session, test_user.tg_id, expected_start, expected_end)
        expected_report_text = formatters(db_data, f"{expected_start:%d.%m.%y} - {expected_end:%d.%m.%y}")

        assert final_kwargs["text"] == expected_report_text

        assert await state.get_state() is None
        assert await state.get_data() == {}

