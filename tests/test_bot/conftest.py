from typing import Any, TypeVar, Dict
import pytest
import os
from pathlib import Path
from datetime import datetime
from aiogram import Dispatcher
from unittest.mock import AsyncMock
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message, User, Chat, CallbackQuery
from aiogram_i18n import I18nMiddleware
#from aiogram_i18n.cores.base import  BaseCore
#from aiogram_i18n.cores import  GNUTextCore
from aiogram.utils.i18n import I18n, I18nMiddleware
from aiogram.types import TelegramObject, Update
from aiogram import Bot

from financial_bot.middlewares import SessionMiddleware
from financial_bot.handlers.transactions import router_tr
from financial_bot.handlers.common import router
from financial_bot.schemas import CreateUser
from  financial_bot.repositories import create_user

current_file_path = Path(__file__).resolve()
base_dir = current_file_path.parent.parent.parent
locales_path = base_dir / "financial_bot" / "locales"

@pytest.fixture
def mock_bot():
    bot = AsyncMock(spec=Bot)
    bot.id = 12345678

    bot.get_me = AsyncMock(return_value=User(
        id=12345678,
        is_bot=True,
        first_name="TestBot",
        username="test_bot"
    ))
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




# class FakeCore(BaseCore):
#     def __init__(self) -> None:
#         # Передаем заглушку пути, так как BaseCore требует его в __init__
#         super().__init__(path=Path("."), default_locale="ru")
#         # Принудительно заполняем словарь locales, чтобы get_translator не падал
#         self.locales = {"ru": self, "en": self}
#
#     # РЕАЛИЗАЦИЯ АБСТРАКТНЫХ МЕТОДОВ (обязательно)
#
#     def get(self, message: str, locale: str | None = None, /, **kwargs: Any) -> str:
#         # Просто возвращаем ключ
#         return message
#
#     def find_locales(self) -> Dict[str, Any]:
#         # Возвращаем фейковый словарь локалей для метода startup
#         return {"ru": self, "en": self}
#
#     # ПЕРЕОПРЕДЕЛЕНИЕ ДЛЯ ТЕСТОВ
#
#     def get_translator(self, locale: str) -> Any:
#         # Возвращаем себя, игнорируя реальный поиск файлов
#         return self
#
#     @property
#     def available_locales(self) -> tuple[str, ...]:
#         return ("ru", "en")
#
#     # Эти методы в BaseCore не абстрактные, но их можно оставить пустыми
#     async def startup(self) -> None:
#         pass
#
#     async def shutdown(self) -> None:
#         pass

class MyI18nMiddleware(I18nMiddleware):
    async def get_locale(self, event: TelegramObject, data: Dict[str, Any]) -> str:
        # В тестах проще всего возвращать дефолтную локаль
        # Или можно достать из event.from_user.language_code
        return self.i18n.default_locale

@pytest.fixture
def test_i18n():
    """Отдельная фикстура для объекта I18n"""
    return I18n(path="financial_bot/locales", default_locale="ru", domain="messages")



@pytest.fixture
async def test_dp(test_session, test_redis, test_i18n):
    # Используем RedisStorage в диспетчере
    storage = RedisStorage(redis=test_redis)
    dp = Dispatcher(storage=storage)

    # i18n_core = GNUTextCore(
    #     path="/application/financial_bot/locales",
    #     default_locale="ru"
    #
    # )



    #i18n_core = FakeCore()

    # i18n_middleware = I18nMiddleware(
    #     core=i18n_core,
    #     default_locale="ru"
    # )
    #i18n_middleware.setup(dp)
    i18n_middleware = MyI18nMiddleware(i18n=test_i18n)
    dp.update.outer_middleware(i18n_middleware)

    dp.update.middleware(SessionMiddleware(session_pool=test_session))
    dp.include_router(router)
    dp.include_router(router_tr)

    return dp




# @pytest.fixture
# def create_mock_update():
#     def _create_message(text: str, user_id: int, update_id: int):
#         # Возвращаем СЛОВАРЬ, имитирующий JSON от Telegram
#         return {
#             "update_id": update_id,
#             "message": {
#                 "message_id": 1,
#                 "date": 12345678,
#                 "chat": {"id": user_id, "type": "private"},
#                 "from": {"id": user_id, "is_bot": False, "first_name": "TestUser"},
#                 "text": text,
#
#             }
#         }
#
#     def _create_callback(data: str, user_id: int, update_id: int):
#         return {
#             "update_id": update_id,
#             "callback_query": {
#                 "id": "123",
#                 "from": {"id": user_id, "is_bot": False, "first_name": "TestUser"},
#                 "data": data,
#                 "chat_instance": "abc",
#
#                 "message": {
#                     "message_id": 2,
#                     "date": 12345678,
#                     "chat": {"id": user_id, "type": "private"},
#                     "text": "Кнопки"
#                 }
#             }
#         }
#
#
#     return _create_message, _create_callback


@pytest.fixture
def create_mock_update(mock_bot): # Передаем сюда фикстуру mock_bot
    def _create_message(text: str, user_id: int, update_id: int):
        # Сразу создаем объект Message, а не словарь
        message = Message(
            message_id=1,
            date=12345678,
            chat=Chat(id=user_id, type="private"),
            from_user=User(id=user_id, is_bot=False, first_name="TestUser"),
            text=text,
            bot=mock_bot  # ПРИВЯЗЫВАЕМ МОК БОТА
        )
        return Update(update_id=update_id, message=message)

    def _create_callback(data: str, user_id: int, update_id: int):
        message = Message(
            message_id=2,
            date=12345678,
            chat=Chat(id=user_id, type="private"),
            text="Кнопки",
            bot=mock_bot
        )
        callback_query = CallbackQuery(
            id="123",
            from_user=User(id=user_id, is_bot=False, first_name="TestUser"),
            data=data,
            chat_instance="abc",
            message=message,
            bot=mock_bot # ПРИВЯЗЫВАЕМ МОК БОТА
        )
        return Update(update_id=update_id, callback_query=callback_query)

    return _create_message, _create_callback