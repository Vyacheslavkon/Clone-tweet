import asyncio
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from loguru import logger

from core.db_worker import get_isolated_session
from financial_bot.handlers.utils import (
    formatters,
    get_month_boundaries,
    get_week_boundaries,
    get_month_name
)
from financial_bot.highload_bot import get_shared_bot
from financial_bot.repositories import (
    blocked_user,
    get_all_users,
    get_reports_for_all_active_users,
    get_plans_for_all_active_users,

)
from services.utils_pipelines import get_translator


async def send_weekly_stats():
    session = get_isolated_session()
    try:
        start_day, end_day = get_week_boundaries()
        all_users = await get_all_users(session)
        reports_by_user = await get_reports_for_all_active_users(session, start_day, end_day)
    finally:
        await session.close()

    bot = get_shared_bot()

    for user in all_users:
        _ = get_translator(user.language_code or "en")
        data_week = reports_by_user.get(user.id, [])
        text = formatters(data_week, "week", period_key="week", translator=_)

        try:
            await bot.send_message(chat_id=user.tg_id, text=text, parse_mode="HTML")
        except TelegramRetryAfter as retry_err:
            await asyncio.sleep(retry_err.retry_after)
            try:
                await bot.send_message(chat_id=user.tg_id, text=text, parse_mode="HTML")
            except Exception as e:
                logger.error("Retry failed for user_id={user_id}: {error}", user_id=user.tg_id, error=e)
        except TelegramForbiddenError:
            logger.warning("User {user_id} blocked the bot. Disabling mailing.", user_id=user.tg_id)
            block_session = get_isolated_session()
            try:
                await blocked_user(block_session, user.tg_id)
                await block_session.commit()
            finally:
                await block_session.close()
        except Exception as e:
            logger.error("Failed to send report to user_id={user_id}: {error}", user_id=user.tg_id, error=e)

        await asyncio.sleep(0.05)

        # # 2. ПОСЛЕРАССЫЛОЧНАЯ ПАКЕТНАЯ ЗАЧИСТКА БАЗЫ (Bulk Update) /it is necessary to think over
        # users_to_block = []
        #except TelegramForbiddenError:
            #logger.warning(f"User {user.tg_id} blocked the bot. Scheduling removal.")
            # Вместо мгновенного коннекта к БД, просто запоминаем ID
            #users_to_block.append(user.tg_id)
        #except Exception as e:
            #logger.error(f"Failed to send report to user_id={user.tg_id}: {e}")
        # check afterwards
        # if users_to_block:
        #     block_session = get_isolated_session()
        #     try:
        #         # Вызываем функцию bulk-апдейта (UPDATE users SET is_active=False WHERE tg_id IN (...))
        #         await blocked_users_bulk(block_session, users_to_block)
        #         await block_session.commit()
        #         logger.info(f"Successfully disabled {len(users_to_block)} blocked users in batch.")
        #     except Exception as e:
        #         await block_session.rollback()
        #         logger.error(f"Failed to execute bulk block update: {e}")
        #     finally:
        #         await block_session.close()

async def send_monthly_stats():
    session = get_isolated_session()
    try:
        start_day, end_day, _month_num = get_month_boundaries()
        all_users = await get_all_users(session)
        reports_by_user = await get_reports_for_all_active_users(session, start_day, end_day)
        plans_by_user = await get_plans_for_all_active_users(session)
    finally:
        await session.close()

    bot = get_shared_bot()

    for user in all_users:
        _ = get_translator(user.language_code or "en")
        data_month = reports_by_user.get(user.id, [])
        planned_data = plans_by_user.get(user.id)
        period = get_month_name(_month_num,  translator=_)
        text = formatters(
            data_month, period, period_key="month",
            plan=planned_data, translator=_,
        )

        try:
            await bot.send_message(chat_id=user.tg_id, text=text, parse_mode="HTML")

        except TelegramRetryAfter as retry_err:
            await asyncio.sleep(retry_err.retry_after)
            try:
                await bot.send_message(chat_id=user.tg_id, text=text, parse_mode="HTML")
            except Exception as e:
                logger.error("Retry failed for user_id={user_id}: {error}", user_id=user.tg_id, error=e)

        except TelegramForbiddenError:
            logger.warning("User {user_id} blocked the bot. Disabling mailing.", user_id=user.tg_id)
            block_session = get_isolated_session()
            try:
                await blocked_user(block_session, user.tg_id)
                await block_session.commit()
            finally:
                await block_session.close()

        except Exception as e:
            logger.error("Failed to send report to user_id={user_id}: {error}", user_id=user.tg_id, error=e)

        await asyncio.sleep(0.05)