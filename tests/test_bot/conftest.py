import pytest
from aiogram import Dispatcher
from unittest.mock import AsyncMock
from aiogram.fsm.storage.redis import RedisStorage

from financial_bot.middlewares import SessionMiddleware
from financial_bot.handlers.transactions import router_tr
from financial_bot.handlers.common import router


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

@pytest.fixture
def create_mock_message(mock_bot):
    def _create(text: str, user_id: int):
        message = AsyncMock()
        message.text = text
        message.from_user.id = user_id
        message.from_user.first_name = "TestUser"
        message.bot = mock_bot
        message.answer = AsyncMock()
        return message

    return _create

@pytest.fixture
def create_mock_callback(mock_bot):
    def _create(data: str, user_id: int):
        callback = AsyncMock()
        callback.data = data  # Данные от кнопки лежат в .data, а не в .text
        callback.from_user.id = user_id
        callback.message.bot = mock_bot
        callback.message.answer = AsyncMock()
        callback.answer = AsyncMock()
        return callback

    return _create
