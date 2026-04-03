# Настройка для aiogram FSM (в bot.py)
import asyncio

from redis.asyncio import Redis
from aiogram.fsm.storage.redis import RedisStorage
from aiogram import Bot, Dispatcher
from aiogram.utils.i18n import I18n

from financial_bot.handlers.start import router_st
from core.config import TOKEN_BOT
from financial_bot.middlewares import  SessionMiddleware, MyI18nMiddleware
from logger_config import setup_logging
from core.database import async_session, engine

redis_fsm = Redis(host='redis', port=6379, db=2)
storage = RedisStorage(redis=redis_fsm)
i18n = I18n(path="locales", default_locale="en", domain="messages")

#redis = Redis.from_url("redis://redis:6379/1") standart



async def main():
    setup_logging()
    bot = Bot(token=TOKEN_BOT)
    dp = Dispatcher(storage=storage)
    session_pool = async_session
    dp.message.outer_middleware(SessionMiddleware(session_pool))
    dp.callback_query.outer_middleware(SessionMiddleware(session_pool))
    dp.message.middleware(MyI18nMiddleware(i18n=i18n))
    dp.include_router(router_st)

    try:
        await dp.start_polling(bot)

    finally:
        await redis_fsm.close()


if __name__ == "__main__":
    asyncio.run(main())
