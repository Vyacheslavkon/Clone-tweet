from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils.i18n import gettext as _
from datetime import datetime, timezone, time
from loguru import logger

from financial_bot.keyboards.inline import period_report
from financial_bot.repositories import get_report_period, get_planned_goals
from financial_bot.filters import I18nTextFilter
from financial_bot.states.generate_report import GenerateReport
from financial_bot.handlers.utils import (formatters,
                                          get_month_boundaries,
                                          get_month_name,
                                          get_week_boundaries,
                                         )



report_rout = Router()

@report_rout.message(I18nTextFilter("Generate report"))
async def reports_period(message: Message, state: FSMContext):

    await message.answer(_("please, select period"), reply_markup=period_report())
    await state.set_state(GenerateReport.waiting_for_period)


@report_rout.callback_query(F.data == "day", GenerateReport.waiting_for_period)
async def  report_day(callback: CallbackQuery, session: AsyncSession):

    if not callback.data or not isinstance(callback.message, Message):
        await callback.answer()
        return

    today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min,
                                   tzinfo=timezone.utc)
    today_end = datetime.combine(datetime.now(timezone.utc).date(), time.max,
                                 tzinfo=timezone.utc)

    data = await get_report_period(session, callback.from_user.id, today_start, today_end)

    period = _("day")

    report_text = formatters(data, period)

    await callback.message.edit_text(text=report_text, parse_mode="HTML")


@report_rout.callback_query(F.data == "week", GenerateReport.waiting_for_period)
async def report_week(callback: CallbackQuery, session: AsyncSession):

    if not callback.data or not isinstance(callback.message, Message):
        await callback.answer()
        return

    period = "week"

    start_day, end_day = get_week_boundaries()

    data = await get_report_period(session, callback.from_user.id, start_day, end_day)

    report_text = formatters(data, period)

    await callback.message.edit_text(text=report_text, parse_mode="HTML")


@report_rout.callback_query(F.data == "month", GenerateReport.waiting_for_period)
async def  report_monthly(callback: CallbackQuery, session: AsyncSession):

    if not callback.data or not isinstance(callback.message, Message):
        await callback.answer()
        return

    start_day, end_day, current_month = get_month_boundaries()

    data = await get_report_period(session, callback.from_user.id, start_day, end_day)
    planned_data = await get_planned_goals(session, callback.from_user.id)

    period = get_month_name(current_month)

    report_text = formatters(data, period, planned_data)

    await callback.message.edit_text(text=report_text, parse_mode="HTML")



