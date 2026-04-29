import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.utils.i18n import I18n, SimpleI18nMiddleware
from redis.asyncio import Redis

from core.config import TOKEN_BOT
from core.database import async_session
from financial_bot.handlers.adding_data import router_data
from financial_bot.handlers.common import router
from financial_bot.handlers.fallback import router_fallback
from financial_bot.handlers.transactions import router_tr
from financial_bot.handlers.reports import report_rout
from financial_bot.middlewares import MyI18nMiddleware, SessionMiddleware
from logger_config import setup_logging

redis_fsm = Redis(host="redis", port=6379, db=2)
storage = RedisStorage(redis=redis_fsm)
i18n = I18n(
    path="/application/financial_bot/locales", default_locale="en", domain="messages"
)


async def main():
    setup_logging()
    bot = Bot(token=TOKEN_BOT)
    dp = Dispatcher(storage=storage)
    session_pool = async_session
    dp.message.outer_middleware(SessionMiddleware(session_pool))
    dp.callback_query.outer_middleware(SessionMiddleware(session_pool))
    dp.message.middleware(MyI18nMiddleware(i18n=i18n))
    dp.update.outer_middleware(SimpleI18nMiddleware(i18n))
    dp.include_router(router)
    dp.include_router(router_tr)
    dp.include_router(router_data)
    dp.include_router(report_rout)
    dp.include_router(router_fallback)

    try:
        await dp.start_polling(bot)

    finally:
        await redis_fsm.close()


if __name__ == "__main__":
    asyncio.run(main())
