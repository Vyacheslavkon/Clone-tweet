from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils.i18n import gettext as _
from datetime import datetime, timezone, time, timedelta
from loguru import logger

from financial_bot.keyboards.inline import period_report, report_history
from financial_bot.repositories import get_report_period
from financial_bot.filters import I18nTextFilter
from financial_bot.states.history_states import HistoryState
from financial_bot.handlers.utils import (formatters,
                                          get_month_boundaries,
                                          get_month_name,
                                          get_week_boundaries,
                                          format_multi_report)



history_rout = Router()


@history_rout.message(I18nTextFilter("History"))
async def reports_history(message: Message, state: FSMContext):

    await message.answer(_("Please, select period"), reply_markup=report_history())
    await state.set_state(HistoryState.waiting_for_period_history)


@history_rout.callback_query(F.data == "two_week", HistoryState.waiting_for_period_history)
async def report_two_weeks(callback: CallbackQuery, session: AsyncSession):

    cur_week = _("current week")
    last_week = _("last week")
    start_cur_week, end_cur_week = get_week_boundaries()
    start_prev_week, end_prev_week = get_week_boundaries(last_week)

    cur_data = await get_report_period(session, callback.from_user.id, start_cur_week, end_cur_week)
    last_data = await get_report_period(session, callback.from_user.id, start_prev_week, end_prev_week)

    report_text = format_multi_report([
        {"data": cur_data, "period_name": cur_week},
        {"data": last_data, "period_name": last_week}
    ])

    await callback.message.answer(report_text, parse_mode="HTML")


