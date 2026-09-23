from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.utils.i18n import gettext as _
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from financial_bot.filters import I18nTextFilter
from financial_bot.handlers.utils import format_transaction_card
from financial_bot.keyboards.inline import get_transaction_carousel_keyboard
from financial_bot.repositories import (
    get_user_by_id,
    get_today_transactions, delete_transaction_by_id,
)
from financial_bot.states.delete_transactions import DeleteTodayState
from services.analysis_cache import FinancialCacheService

router_del_transactions = Router()


@router_del_transactions.message(I18nTextFilter("Delete today's data"))
async def handle_delete_today_request(message: Message, session: AsyncSession, state: FSMContext):
    user = await get_user_by_id(session, message.from_user.id)
    if not user:
        return

    transactions = await get_today_transactions(session, user.id)

    if not transactions:
        await message.answer(_("You have no transactions logged today. 🤷"))
        return

    tx_data = [
        {
            "id": tx.id,
            "category": tx.category,
            "amount": float(tx.amount),
            "type": tx.type,
            "created_at": tx.created_at.isoformat(),
            "description": tx.description,
        }
        for tx in transactions
    ]

    await state.set_state(DeleteTodayState.browsing)
    await state.update_data(tx_data=tx_data, current_index=0)

    await message.answer(
        format_transaction_card(tx_data[0], _),
        reply_markup=get_transaction_carousel_keyboard(tx_data, 0, _),
        parse_mode="HTML",
    )


@router_del_transactions.callback_query(F.data.startswith("tx_nav:"), DeleteTodayState.browsing)
async def handle_carousel_navigation(callback: CallbackQuery, state: FSMContext):
    raw_index = callback.data.split(":")[1]
    if raw_index == "noop":
        await callback.answer()
        return

    new_index = int(raw_index)
    data = await state.get_data()
    tx_data = data["tx_data"]

    await state.update_data(current_index=new_index)

    await callback.message.edit_text(
        format_transaction_card(tx_data[new_index], _),
        reply_markup=get_transaction_carousel_keyboard(tx_data, new_index, _),
        parse_mode="HTML",
    )
    await callback.answer()


@router_del_transactions.callback_query(F.data.startswith("tx_delete:"), DeleteTodayState.browsing)
async def handle_carousel_delete(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession,
    cache_service: FinancialCacheService,
    ):
    tx_id = int(callback.data.split(":")[1])
    user = await get_user_by_id(session, callback.from_user.id)

    deleted = await delete_transaction_by_id(session, tx_id, user_id=user.id)
    await session.commit()

    if not deleted:
        await callback.answer(_("Already deleted."), show_alert=True)
        return

    try:
        await cache_service.invalidate_user_cache(user_id=user.id)
    except Exception as e:
        logger.error("Failed to invalidate cache: {error}", error=e)

    data = await state.get_data()
    tx_data = [tx for tx in data["tx_data"] if tx["id"] != tx_id]  # убираем удалённую из локального списка

    if not tx_data:
        await callback.message.edit_text(_("✅ Deleted. No more transactions for today."))
        await state.clear()
        await callback.answer()
        return

    current_index = min(data["current_index"], len(tx_data) - 1)
    await state.update_data(tx_data=tx_data, current_index=current_index)

    await callback.message.edit_text(
        format_transaction_card(tx_data[current_index], _),
        reply_markup=get_transaction_carousel_keyboard(tx_data, current_index, _),
        parse_mode="HTML",
    )
    await callback.answer(_("✅ Deleted"))


@router_del_transactions.callback_query(F.data == "tx_close", DeleteTodayState.browsing)
async def handle_carousel_close(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(_("Closed."))
    await state.clear()