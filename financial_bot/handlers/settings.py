from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.i18n import gettext as _
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from financial_bot.filters import I18nTextFilter
from financial_bot.keyboards.inline import get_timezone_keyboard
from financial_bot.keyboards.reply import settings, get_main_menu
from financial_bot.repositories import (
    get_user_by_id,
)
from financial_bot.handlers.utils import is_valid_timezone
from financial_bot.states.settings_states import SettingsState

from services.analysis_cache import FinancialCacheService

settings_router = Router()


@settings_router.message(I18nTextFilter("Settings"))
async def handle_settings(message: Message):
    await message.answer(_("Select the required option:"), reply_markup=settings())



@settings_router.message(I18nTextFilter("Change timezone"))
async def handle_timezone_settings(message: Message):
    await message.answer(
        _("Select your timezone, or enter it manually (e.g. 'Asia/Tokyo'):"),
        reply_markup=get_timezone_keyboard())


@settings_router.callback_query(F.data.startswith("set_tz:"))
async def handle_timezone_selection(
    callback: CallbackQuery, session: AsyncSession, cache_service: FinancialCacheService
):
    tz_value = callback.data.split(":", 1)[1]

    if not is_valid_timezone(tz_value):
        await callback.answer(_("Invalid timezone."), show_alert=True)
        return

    user = await get_user_by_id(session, callback.from_user.id)
    if not user:
        await callback.answer()
        return

    user.timezone = tz_value
    await session.commit()

    try:
        await cache_service.invalidate_user_cache(user_id=user.id)
    except Exception as e:
        logger.error("Failed to invalidate cache after timezone change: {error}", error=e)

    #await callback.message.edit_text(_("✅ Timezone updated to {tz}").format(tz=tz_value))

    await callback.message.delete()

    # test
    await callback.message.answer(
        _("✅ The settings have been saved successfully. The time zone has been changed to: <b>{tz}</b>").format(tz=tz_value),
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@settings_router.callback_query(F.data == "set_tz_manual")
async def handle_timezone_manual_request(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.waiting_for_custom_timezone)
    await callback.message.edit_text(
        _("Please type the timezone name, e.g. 'Asia/Tokyo' or 'America/Chicago'.\n\n"
          "You can find the full list here: "
          "https://en.wikipedia.org/wiki/List_of_tz_database_time_zones")
    )
    await callback.answer()


@settings_router.message(SettingsState.waiting_for_custom_timezone)
async def handle_timezone_manual_input(
    message: Message, session: AsyncSession, state: FSMContext, cache_service: FinancialCacheService
):
    tz_value = message.text.strip()

    if not is_valid_timezone(tz_value):
        await message.answer(
            _("❌ '{tz}' is not a valid timezone name. Please try again, "
              "e.g. 'Europe/Paris' or 'Asia/Singapore'.").format(tz=tz_value)
        )
        return  # остаёмся в том же состоянии, даём попробовать ещё раз

    user = await get_user_by_id(session, message.from_user.id)
    if not user:
        await state.clear()
        return

    user.timezone = tz_value
    await session.commit()

    try:
        await cache_service.invalidate_user_cache(user_id=user.id)
    except Exception as e:
        logger.error("Failed to invalidate cache after timezone change: {error}", error=e)

    await state.clear()
    await message.answer(_("✅ Timezone updated to {tz}").format(tz=tz_value),
                         reply_markup=get_main_menu())



async def _apply_timezone(
    callback: CallbackQuery, session: AsyncSession,
    cache_service: FinancialCacheService, tz_value: str,
):
    """Общая логика применения пояса — переиспользуется и для выбора из
    списка, и потенциально для других путей выбора в будущем."""
    if not is_valid_timezone(tz_value):
        await callback.answer(_("Invalid timezone."), show_alert=True)
        return

    user = await get_user_by_id(session, callback.from_user.id)
    if not user:
        await callback.answer()
        return

    user.timezone = tz_value
    await session.commit()

    try:
        await cache_service.invalidate_user_cache(user_id=user.id)
    except Exception as e:
        logger.error("Failed to invalidate cache after timezone change: {error}", error=e)

    await callback.message.edit_text(_("✅ Timezone updated to {tz}").format(tz=tz_value))
    await callback.answer()