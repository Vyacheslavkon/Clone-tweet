import pytest
from redis.asyncio import Redis
from aiogram import Dispatcher
from unittest.mock import AsyncMock
from aiogram.fsm.storage.redis import RedisStorage

from financial_bot.middlewares import SessionMiddleware
from financial_bot.handlers.transactions import router_tr
from financial_bot.handlers.common import router

@pytest.fixture
async def test_redis():
    # Внутри Docker используем имя сервиса 'test_redis'
    redis = Redis(host='test_redis', port=6379, db=3)
    yield redis
    await redis.flushdb()
    await redis.close()


@pytest.fixture
def mock_bot():
    """Создает мок бота, который не делает реальных запросов"""
    bot = AsyncMock()
    bot.id = 12345678
    return bot


@pytest.fixture
async def test_dp(test_session, test_redis):
    # Используем RedisStorage в диспетчере
    storage = RedisStorage(redis=test_redis)
    dp = Dispatcher(storage=storage)

    # Подключаем Middleware и роутеры
    dp.update.middleware(SessionMiddleware(session_pool=test_session))
    dp.include_router(router)
    dp.include_router(router_tr)

    return dp