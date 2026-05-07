from aiogram.utils.i18n import I18n
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from sqlalchemy.ext.asyncio import async_sessionmaker
from loguru import logger

from financial_bot.handlers.utils import (formatters,
                                          get_week_boundaries,
                                          get_month_boundaries)

from financial_bot.repositories import get_report_period, get_all_users, get_planned_goals


async def send_weekly_stats(bot: Bot, session_pool: async_sessionmaker, i18n: I18n):
   async with session_pool() as session:
       start_day, end_day = get_week_boundaries()
       all_users_id = await get_all_users(session)

       for user in all_users_id:
            with i18n.use_locale(user.language_code or "en"):
                I18n.set_current(i18n)
                data_week = await get_report_period(session, user.tg_id, start_day, end_day)
                text = formatters(data_week, "week")
                try:
                    await bot.send_message(chat_id=user.tg_id, text=text, parse_mode="HTML")
                except Exception as e:

                    logger.error(f"Не удалось отправить отчет {user.tg_id}: {e}")


async def send_monthly_stats(bot: Bot, session_pool: async_sessionmaker, i18n: I18n):
    async with session_pool() as session:
        start_day, end_day, _ = get_month_boundaries()
        all_users_id = await get_all_users(session)

        for user in all_users_id:
            with i18n.use_locale(user.language_code or "en"):
                I18n.set_current(i18n)
                data_month = await get_report_period(session, user.tg_id, start_day, end_day)
                planned_data = await get_planned_goals(session, user.tg_id)
                text = formatters(data_month, "month", planned_data)
                try:
                    await bot.send_message(chat_id=user.tg_id, text=text, parse_mode="HTML")
                except Exception as e:

                    logger.error(f"Не удалось отправить отчет {user.tg_id}: {e}")


def setup_scheduler(bot: Bot, session_pool: async_sessionmaker, i18n: I18n) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    scheduler.add_job(send_weekly_stats, "cron", day_of_week="thu", hour=14, minute=45, kwargs={
                                                                            "bot": bot,
                                                                            "session_pool": session_pool,
                                                                            "i18n": i18n
                                                                        })

    # scheduler.add_job(send_monthly_stats,  "interval", seconds=10, kwargs={
    #                                                                         "bot": bot,
    #                                                                         "session_pool": session_pool,
    #                                                                         "i18n": i18n
    #                                                                     })
    scheduler.add_job(send_monthly_stats, "cron", day=7, hour=14, minute=45, kwargs={
                                                                            "bot": bot,
                                                                            "session_pool": session_pool,
                                                                            "i18n": i18n
                                                                        })

    return scheduler



