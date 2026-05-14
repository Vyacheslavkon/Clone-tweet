from sqlalchemy import select
import pytest
from datetime import datetime, timezone, time, timedelta
from unittest.mock import patch, AsyncMock
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import EditMessageText
from financial_bot.schemas import AddData
from financial_bot.states.generate_report import GenerateReport
from financial_bot.models import Transactions
from financial_bot.repositories import get_report_period, get_planned_goals
from financial_bot.handlers.utils import formatters
from tests.test_bot.utils import get_expected_timestamps

from tests.test_bot.utils import (
    called_bot,
    comparison_dict,
    dict_invalid_data,
    keyboard_check,
    kb_reports,
)


async def test_report_period(test_dp, create_mock_update, mock_bot, test_i18n, test_user):

    create_message, _ = create_mock_update
    user_id = test_user.id

    text = test_i18n.gettext("Generate report")
    msg_first = create_message(text=text, user_id=user_id, update_id=1)
    await test_dp.feed_update(mock_bot, msg_first)
    expected_text = test_i18n.gettext("please, select period")
    called_bot(mock_bot, expected_text)

    buttons = kb_reports()

    keyboard_check(buttons, mock_bot, test_i18n)

    state = test_dp.fsm.get_context(bot=mock_bot, chat_id=user_id, user_id=user_id)
    current_state = await state.get_state()
    assert current_state == GenerateReport.waiting_for_period.state



# async def test_report_day(mock_bot, test_dp, create_mock_update,
#                     test_i18n, test_user, test_transaction, test_session):
#    mock_bot.id = 12345678
#
#    test_dp["bot"] = mock_bot
#
#    _, create_callback = create_mock_update
#
#    state = test_dp.fsm.get_context(bot=mock_bot, user_id=test_user.tg_id, chat_id=test_user.tg_id)
#    await state.set_state(GenerateReport.waiting_for_period)
#
#    callback_message = create_callback(data="day", user_id=test_user.tg_id, update_id=1)
#
#    with test_i18n.context():
#        await test_dp.feed_update(mock_bot, callback_message)
#
#        today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
#        today_end = datetime.combine(datetime.now(timezone.utc).date(), time.max, tzinfo=timezone.utc)
#
#        data = await get_report_period(test_session, test_user.tg_id, today_start, today_end)
#        period = "day"
#        expected_data = formatters(data, period)
#
#        mock_bot.edit_message_text.assert_called_once()
#        _, kwargs = mock_bot.edit_message_text.call_args
#
#        assert kwargs["text"] == expected_data
#        assert kwargs["chat_id"] == test_user.tg_id
#        assert kwargs["message_id"] == 2


@pytest.mark.parametrize(
    "period, callback_data",
    [
        ("day", "day"),
        ("week", "week"),
        #("month", "month"),
    ]
)
async def test_report_periods(
        mock_bot, test_dp, create_mock_update, test_i18n,
        test_user, test_transaction, test_session, period, callback_data, test_data
):
    mock_bot.id = 12345678
    test_dp["bot"] = mock_bot

    _, create_callback = create_mock_update

    state = test_dp.fsm.get_context(bot=mock_bot, user_id=test_user.tg_id, chat_id=test_user.tg_id)
    await state.set_state(GenerateReport.waiting_for_period)

    callback_message = create_callback(data=callback_data, user_id=test_user.tg_id, update_id=1)

    with test_i18n.context():
        await test_dp.feed_update(mock_bot, callback_message)

        today_start, today_end = get_expected_timestamps(period)

        data = await get_report_period(test_session, test_user.tg_id, today_start, today_end)
        #planned_data = await get_planned_goals(test_session, test_user.tg_id)
        expected_data = formatters(data, period)

        mock_bot.edit_message_text.assert_called_once()
        _, kwargs = mock_bot.edit_message_text.call_args

        assert kwargs["text"] == expected_data
        assert kwargs["chat_id"] == test_user.tg_id
        assert kwargs["message_id"] == 2


