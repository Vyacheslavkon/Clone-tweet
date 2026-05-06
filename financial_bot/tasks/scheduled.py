from aiogram.utils.i18n import I18n
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from sqlalchemy.ext.asyncio import async_sessionmaker
from loguru import logger

from financial_bot.handlers.utils import (formatters,
                                          get_week_boundaries,
                                          get_month_boundaries)

from financial_bot.repositories import get_report_period, get_all_users_id


# async def send_weekly_stats(bot: Bot, session_pool: async_sessionmaker,  i18n: I18n):
#    async with session_pool() as session:
#        start_day, end_day = get_week_boundaries()
#        all_users_id = await get_all_users_id(session)
#
#        for user_id in all_users_id:
#            # with i18n.context():
#            #      i18n.set_locale(user.language_code or "en")  # Берем язык из БД
#             data_week = await get_report_period(session, user_id, start_day, end_day)
#             text = formatters(data_week, "week")
#             try:
#                 await bot.send_message(chat_id=user_id, text=text)
#             except Exception as e:
#                 # Логируем, если пользователь заблокировал бота, и идем дальше
#                 logger.error(f"Не удалось отправить отчет {user_id}: {e}")
#
#
# async def send_monthly_stats(bot: Bot, session_pool: async_sessionmaker):
#     # Логика...
#     pass
#
#
# def setup_scheduler(bot: Bot, session_pool: async_sessionmaker, i18n: I18n) -> AsyncIOScheduler:
#     scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
#
#     # Регистрация задач
#     #scheduler.add_job(send_weekly_stats, "cron", day_of_week="wed", hour=23, minute=18,  args=[bot, session_pool])
#     scheduler.add_job(send_weekly_stats,  "interval", seconds=10,  args=[bot, session_pool, i18n])
#     #scheduler.add_job(send_monthly_stats, "cron", day=1, hour=9, args=[bot])
#
#     return scheduler



