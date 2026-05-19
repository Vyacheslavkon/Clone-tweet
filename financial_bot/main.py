import asyncio
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.utils.i18n import I18n, SimpleI18nMiddleware
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker

from core.config import TOKEN_BOT
from core.database import async_session
from financial_bot.handlers.adding_data import router_data
from financial_bot.handlers.common import router
from financial_bot.handlers.fallback import router_fallback
from financial_bot.handlers.transactions import router_tr
from financial_bot.handlers.reports import report_rout
from financial_bot.handlers.history import history_rout
from financial_bot.handlers.settings import set_router
from financial_bot.middlewares import MyI18nMiddleware, SessionMiddleware, UserActivityMiddleware
from financial_bot.tasks.scheduled import setup_scheduler
from logger_config import setup_logging

redis_fsm = Redis(host="redis", port=6379, db=2)
storage = RedisStorage(redis=redis_fsm)
i18n = I18n(
    path="/application/financial_bot/locales", default_locale="en", domain="messages"
)


async def main():
    load_dotenv()
    setup_logging()
    bot = Bot(token=TOKEN_BOT)
    dp = Dispatcher(storage=storage)
    session_pool = async_session
    scheduler = setup_scheduler(bot, session_pool, i18n)
    dp["admin_id"] = int(os.getenv("ADMIN_ID", 0))
    dp.message.outer_middleware(SessionMiddleware(session_pool))
    dp.callback_query.outer_middleware(SessionMiddleware(session_pool))
    dp.message.middleware(MyI18nMiddleware(i18n=i18n))
    dp.update.outer_middleware(SimpleI18nMiddleware(i18n))
    dp.update.outer_middleware(UserActivityMiddleware())
    dp.include_router(router)
    dp.include_router(router_tr)
    dp.include_router(router_data)
    dp.include_router(report_rout)
    dp.include_router(history_rout)
    dp.include_router(set_router)
    dp.include_router(router_fallback)

    try:
        scheduler.start()
        await dp.start_polling(bot)

    finally:
        await redis_fsm.close()
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
