from unittest.mock import MagicMock

from aiogram.utils.i18n import I18n
from aiogram.utils.i18n import gettext as _

from financial_bot.handlers.utils import (
    formatters,
    get_month_boundaries,
    get_week_boundaries,
)
from financial_bot.repositories import get_planned_goals, get_report_period
from financial_bot.tasks.scheduled import send_monthly_stats, send_weekly_stats


async def test_send_weekly_stats(
    test_session, mock_bot, test_i18n, test_user, test_data, test_transaction
):

    I18n.set_current(test_i18n)
    start_day, end_day = get_week_boundaries()

    session_pool_mock = MagicMock()

    session_pool_mock.return_value = test_session
    # session_pool_mock.return_value.__aenter__.return_value = test_session
    # session_pool_mock.return_value.__aexit__ = AsyncMock(return_value=None)

    user_locale = test_user.language_code or "en"
    with test_i18n.use_locale(user_locale):
        data_week = await get_report_period(
            test_session, test_user.tg_id, start_day, end_day
        )

        expected_data = formatters(data_week, _("week"))

    await send_weekly_stats(mock_bot, session_pool_mock, test_i18n)

    mock_bot.send_message.assert_called_once_with(
        chat_id=test_user.tg_id, text=expected_data, parse_mode="HTML"
    )


async def test_send_month_stats(
    test_session, mock_bot, test_i18n, test_user, test_data, test_transaction
):

    I18n.set_current(test_i18n)
    start_day, end_day, _month_num = get_month_boundaries()

    session_pool_mock = MagicMock()

    session_pool_mock.return_value = test_session

    user_locale = test_user.language_code or "en"
    with test_i18n.use_locale(user_locale):
        data_week = await get_report_period(
            test_session, test_user.tg_id, start_day, end_day
        )
        planned_data = await get_planned_goals(test_session, test_user.tg_id)
        expected_data = formatters(data_week, _("month"), planned_data)

    await send_monthly_stats(mock_bot, session_pool_mock, test_i18n)

    mock_bot.send_message.assert_called_once_with(
        chat_id=test_user.tg_id, text=expected_data, parse_mode="HTML"
    )
