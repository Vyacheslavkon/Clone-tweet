import copy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import CallbackQuery, Chat, Message, TelegramObject, Update, User
from aiogram.utils.i18n import I18n, I18nMiddleware

from financial_bot.handlers.adding_data import router_data
from financial_bot.handlers.common import router
from financial_bot.handlers.transactions import router_tr
from financial_bot.middlewares import SessionMiddleware
from financial_bot.repositories import add_data_for_user, create_user
from financial_bot.schemas import AddData, CreateUser

current_file_path = Path(__file__).resolve()
base_dir = current_file_path.parent.parent.parent
locales_path = base_dir / "financial_bot" / "locales"


@pytest.fixture
def mock_bot():
    bot = AsyncMock(spec=Bot)
    bot.id = 12345678

    bot.get_me = AsyncMock(
        return_value=User(
            id=12345678, is_bot=True, first_name="TestBot", username="test_bot"
        )
    )
    return bot


@pytest.fixture
async def test_user(test_session):
    data = {
        "tg_id": 12345,
        "language_code": "ru",
        "first_name": "TestUser",
    }

    new_user = CreateUser(**data)

    await create_user(test_session, new_user)

    return new_user


class MyI18nMiddleware(I18nMiddleware):
    async def get_locale(self, event: TelegramObject, data: Dict[str, Any]) -> str:
        # В тестах проще всего возвращать дефолтную локаль
        # Или можно достать из event.from_user.language_code
        return self.i18n.default_locale


@pytest.fixture
def test_i18n():
    """Отдельная фикстура для объекта I18n"""
    return I18n(path="financial_bot/locales", default_locale="en", domain="messages")


@pytest.fixture
async def test_dp(test_session, test_redis, test_i18n):

    storage = RedisStorage(redis=test_redis)
    dp = Dispatcher(storage=storage)

    i18n_middleware = MyI18nMiddleware(i18n=test_i18n)
    dp.update.outer_middleware(i18n_middleware)

    dp.update.middleware(SessionMiddleware(session_pool=test_session))

    for r in [router, router_tr, router_data]:
        if r is not None:

            new_router = copy.deepcopy(r)
            dp.include_router(new_router)
        else:
            raise ValueError(
                "One of the routers (router или router_tr) "
                "is not imported or is equal None"
            )

    return dp


@pytest.fixture
def create_mock_update(mock_bot):
    def _create_message(text: str, user_id: int, update_id: int):

        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=user_id, type="private"),
            from_user=User(
                id=user_id, is_bot=False, first_name="TestUser", language_code="ru"
            ),
            text=text,
            bot=mock_bot,
        )
        return Update(update_id=update_id, message=message)

    def _create_callback(data: str, user_id: int, update_id: int):
        message = Message(
            message_id=2,
            date=datetime.now(),
            chat=Chat(id=user_id, type="private"),
            text="Кнопки",
            bot=mock_bot,
        )
        callback_query = CallbackQuery(
            id="123",
            from_user=User(id=user_id, is_bot=False, first_name="TestUser"),
            data=data,
            chat_instance="abc",
            message=message,
            bot=mock_bot,
        )
        return Update(update_id=update_id, callback_query=callback_query)

    return _create_message, _create_callback


@pytest.fixture
async def budget(test_session, test_user):

    new_obg = AddData(monthly_budget="2000")

    await add_data_for_user(test_session, new_obg, test_user.tg_id)

    return new_obg
