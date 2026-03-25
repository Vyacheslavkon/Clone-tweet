# Настройка для aiogram FSM (в bot.py)
import asyncio

from redis.asyncio import Redis
from aiogram.fsm.storage.redis import RedisStorage
from aiogram import Bot, Dispatcher

from core.config import TOKEN_BOT

redis_fsm = Redis(host='redis', port=6379, db=2)
storage = RedisStorage(redis=redis_fsm)


#redis = Redis.from_url("redis://redis:6379/1") standart





# 3. Передаем хранилище в диспетчер
dp = Dispatcher(storage=storage)

async def main():
    bot = Bot(token=TOKEN_BOT)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
