# Настройка для aiogram FSM (в bot.py)
from redis.asyncio import Redis
from aiogram.fsm.storage.redis import RedisStorage

redis_fsm = Redis(host='redis', port=6379, db=1)
storage = RedisStorage(redis=redis_fsm)



import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis # Важно использовать асинхронный клиент

# 1. Подключаемся к Redis (адрес по умолчанию)
redis = Redis(host='redis', port=6379, db=1)
#redis = Redis.from_url("redis://redis:6379/1") standart


# 2. Создаем хранилище на базе Redis
storage = RedisStorage(redis=redis)

# 3. Передаем хранилище в диспетчер
dp = Dispatcher(storage=storage)

async def main():
    bot = Bot(token="ВАШ_ТОКЕН")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
