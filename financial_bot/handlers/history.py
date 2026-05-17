from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils.i18n import gettext as _
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
from datetime import datetime

from financial_bot.keyboards.inline import report_history
from financial_bot.repositories import get_report_period
from financial_bot.filters import I18nTextFilter
from financial_bot.states.history_states import HistoryState
from financial_bot.handlers.utils import (formatters,
                                          get_week_boundaries,
                                          format_multi_report,
                                          get_arbitrary_period)



history_rout = Router()


@history_rout.message(I18nTextFilter("History"))
async def reports_history(message: Message, state: FSMContext):

    await message.answer(_("Please, select period"), reply_markup=report_history())
    await state.set_state(HistoryState.waiting_for_period_history)


@history_rout.callback_query(F.data == "two_week", HistoryState.waiting_for_period_history)
async def report_two_weeks(callback: CallbackQuery, session: AsyncSession, bot: Bot):

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

    await bot.send_message(text=report_text, chat_id=callback.message.chat.id, parse_mode="HTML")




@history_rout.callback_query(F.data == "period", HistoryState.waiting_for_period_history)
async def report_arbitrary_period(callback: CallbackQuery, state: FSMContext, bot: Bot):

    await bot.send_message(text=
        _("📅 Select the <b>start date</b> of the period:"),
        chat_id=callback.from_user.id,
        reply_markup=await SimpleCalendar().start_calendar(),
        parse_mode="HTML"
    )

    await state.set_state(HistoryState.waiting_for_data_start)


@history_rout.callback_query(SimpleCalendarCallback.filter(), HistoryState.waiting_for_data_start)
async def process_start_date(callback: CallbackQuery,
                             callback_data: SimpleCalendarCallback,
                             state: FSMContext, bot: Bot):

    selected, date = await SimpleCalendar().process_selection(callback, callback_data)

    if selected:
        await state.update_data(start_date=date.isoformat())
        await state.set_state(HistoryState.waiting_for_data_end)

        await bot.edit_message_text(
            _("✅ Start date: {selected_date}\n"
            "📅 Now select the <b>end date</b>:\n"
            "(click the same date again if you need a report for one day)").
            format(selected_date=date.strftime('%d.%m.%Y')),
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            parse_mode="HTML"
        )

        await  bot.edit_message_reply_markup(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            reply_markup=await SimpleCalendar().start_calendar()
                 )



@history_rout.callback_query(SimpleCalendarCallback.filter(), HistoryState.waiting_for_data_end)
async def process_end_date(callback: CallbackQuery,
                           callback_data: SimpleCalendarCallback,
                           state: FSMContext,
                           session: AsyncSession,
                           bot: Bot):

    selected, date = await SimpleCalendar().process_selection(callback, callback_data)

    if selected:
        user_data = await state.get_data()
        start_date = datetime.fromisoformat(user_data['start_date'])
        end_date = date

        start_date, end_date = get_arbitrary_period(start_date, end_date)

        data = await get_report_period(session, callback.from_user.id, start_date, end_date)
        report_text = formatters(data, f"{start_date:%d.%m.%y} - {end_date:%d.%m.%y}")

        await bot.send_message(text=report_text, chat_id=callback.message.chat.id, parse_mode="HTML")
        await state.clear()