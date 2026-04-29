from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils.i18n import gettext as _
from loguru import logger

from financial_bot.keyboards.inline import period_report
from financial_bot.repositories import get_income_day
from financial_bot.filters import I18nTextFilter
from financial_bot.states.generate_report import GenerateReport


report_rout = Router()

@report_rout.message(I18nTextFilter("Generate report"))
async def reports_period(message: Message, state: FSMContext):

    await message.answer(_("please, select period"), reply_markup=period_report())
    await state.set_state(GenerateReport.waiting_for_period)


@report_rout.callback_query(F.data == "day", GenerateReport.waiting_for_period)
async def  report_day(callback: CallbackQuery, session: AsyncSession,  state: FSMContext):

    # if not callback.data or not isinstance(callback.message, Message):
    #     await callback.answer()
    #     return

    # report = await get_income_day(session, callback.from_user.id)
    #
    # await callback.message.edit_text(report)
    # await callback.answer()

    data = await get_income_day(session, callback.from_user.id)

    if not data:
        report_text = "Данных за сегодня нет 🤷‍♂️"
    else:
        income_total = 0
        expense_total = 0
        income_details = ""
        expense_details = ""

        for row in data:
            # row.type, row.category, row.total
            if row.type == 'income':
                income_total += row.total
                income_details += f"  • {row.category}: {row.total}\n"
            else:
                expense_total += row.total
                expense_details += f"  • {row.category}: {row.total}\n"

        report_text = (
            f"<b>Отчет за сегодня:</b>\n\n"
            f"💰 <b>Доходы: {income_total}</b>\n{income_details}"
            f"\n"
            f"💸 <b>Расходы: {expense_total}</b>\n{expense_details}"
        )

    # Теперь передаем сформированную СТРОКУ
    await callback.message.edit_text(text=report_text, parse_mode="HTML")