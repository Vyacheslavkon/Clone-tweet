from aiogram.utils.i18n import gettext as _
from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from financial_bot.filters import I18nTextFilter
from financial_bot.states.add_data_states import AddDataState

router_data = Router()


@router_data.message(I18nTextFilter("Add/change data"))
async def data_selection(message: Message, state: FSMContext):

    await message.answer(_("Please, select data type"))
    await state.set_state(AddDataState.waiting_for_type_data)


@router_data.message(AddDataState.waiting_for_type_data)
async def add_data(message: Message, session: AsyncSession ):

    pass

