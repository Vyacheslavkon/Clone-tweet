# Настройка для aiogram FSM (в bot.py)
import asyncio

from redis.asyncio import Redis
from aiogram.fsm.storage.redis import RedisStorage
from aiogram import Bot, Dispatcher

from financial_bot.handlers.start import router_st
from core.config import TOKEN_BOT
from financial_bot.middlewares import DbSessionMiddleware
from logger_config import setup_logging

redis_fsm = Redis(host='redis', port=6379, db=2)
storage = RedisStorage(redis=redis_fsm)


#redis = Redis.from_url("redis://redis:6379/1") standart





# 3. Передаем хранилище в диспетчер
#dp = Dispatcher(storage=storage)

async def main():
    setup_logging()
    bot = Bot(token=TOKEN_BOT)
    dp = Dispatcher(storage=storage)
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.include_router(router_st)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
