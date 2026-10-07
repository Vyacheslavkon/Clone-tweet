from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.i18n import gettext as _
from aiogram.utils.i18n.context import get_i18n
from loguru import logger
from redis import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from financial_bot.filters import I18nTextFilter
from financial_bot.general_utils import (
    SUPPORTED_CURRENCY_CODES,
    SUPPORTED_LANGUAGE_CODES,
)
from financial_bot.handlers.utils import is_valid_timezone
from financial_bot.keyboards.inline import (
    get_currency_keyboard,
    get_language_keyboard,
    get_timezone_keyboard,
)
from financial_bot.keyboards.reply import get_main_menu, settings
from financial_bot.repositories import (
    get_user_by_id,
)
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
        reply_markup=get_timezone_keyboard(),
    )


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
    except RedisError as e:
        logger.error(
            "Failed to invalidate cache after timezone change: {error}", error=e
        )

    # await callback.message.edit_text(_("✅ Timezone updated to {tz}").format(tz=tz_value))

    await callback.message.delete()

    # test
    await callback.message.answer(
        _(
            "✅ The settings have been saved successfully. The time zone has been changed to: <b>{tz}</b>"
        ).format(tz=tz_value),
        reply_markup=get_main_menu(),
        parse_mode="HTML",
    )
    await callback.answer()


@settings_router.callback_query(F.data == "set_tz_manual")
async def handle_timezone_manual_request(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.waiting_for_custom_timezone)
    await callback.message.edit_text(
        _(
            "Please type the timezone name, e.g. 'Asia/Tokyo' or 'America/Chicago'.\n\n"
            "You can find the full list here: "
            "https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
        )
    )
    await callback.answer()


@settings_router.message(SettingsState.waiting_for_custom_timezone)
async def handle_timezone_manual_input(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    cache_service: FinancialCacheService,
):
    tz_value = message.text.strip()

    if not is_valid_timezone(tz_value):
        await message.answer(
            _(
                "❌ '{tz}' is not a valid timezone name. Please try again, "
                "e.g. 'Europe/Paris' or 'Asia/Singapore'."
            ).format(tz=tz_value)
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
    except RedisError as cache_err:
        logger.error(
            "Failed to invalidate cache after timezone change: {error}", error=cache_err
        )

    await state.clear()
    await message.answer(
        _("✅ Timezone updated to {tz}").format(tz=tz_value),
        reply_markup=get_main_menu(),
    )


async def _apply_timezone(
    callback: CallbackQuery,
    session: AsyncSession,
    cache_service: FinancialCacheService,
    tz_value: str,
):

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
    except RedisError as cache_err:
        logger.error(
            "Failed to invalidate cache after timezone change: {error}", error=cache_err
        )

    await callback.message.edit_text(
        _("✅ Timezone updated to {tz}").format(tz=tz_value)
    )
    await callback.answer()


@settings_router.message(I18nTextFilter("Change language"))
async def handle_language_settings(message: Message):
    await message.answer(
        _("Select your language:"), reply_markup=get_language_keyboard()
    )


@settings_router.callback_query(F.data.startswith("set_lang:"))
async def handle_language_selection(
    callback: CallbackQuery, session: AsyncSession, cache_service: FinancialCacheService
):
    lang = callback.data.split(":", 1)[1]

    if lang not in SUPPORTED_LANGUAGE_CODES:
        await callback.answer(_("Unsupported language."), show_alert=True)
        return

    user = await get_user_by_id(session, callback.from_user.id)
    if not user:
        await callback.answer()
        return

    user.language_code = lang
    await session.commit()

    try:
        await cache_service.invalidate_user_cache(user_id=user.id)
    except RedisError as e:
        logger.error(
            "Failed to invalidate cache after language change: {error}", error=e
        )

    with get_i18n().use_locale(lang):
        confirmation = _("✅ Language updated")
        menu = get_main_menu()

    await callback.message.answer(confirmation, reply_markup=menu)
    await callback.answer()


@settings_router.message(I18nTextFilter("Change currency"))
async def handle_currency_settings(message: Message):
    await message.answer(
        _(
            "Select your currency. Note: this only changes how amounts are displayed, "
            "existing values are NOT converted."
        ),
        reply_markup=get_currency_keyboard(),
    )


@settings_router.callback_query(F.data.startswith("set_cur:"))
async def handle_currency_selection(
    callback: CallbackQuery, session: AsyncSession, cache_service: FinancialCacheService
):
    currency = callback.data.split(":", 1)[1]

    if currency not in SUPPORTED_CURRENCY_CODES:
        await callback.answer(_("Unsupported currency."), show_alert=True)
        return

    user = await get_user_by_id(session, callback.from_user.id)
    if not user:
        await callback.answer()
        return

    user.currency = currency
    await session.commit()

    try:
        await cache_service.invalidate_user_cache(user_id=user.id)
    except RedisError as e:
        logger.error(
            "Failed to invalidate cache after currency change: {error}", error=e
        )

    confirmation = _("✅ Currency updated to {currency}").format(currency=currency)
    # await callback.message.edit_text(confirmation)
    await callback.message.answer(confirmation, reply_markup=get_main_menu())
    await callback.answer()
