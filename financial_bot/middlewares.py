from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.types import Update
from aiogram.utils.i18n import I18nMiddleware
from aiogram.utils.i18n import gettext as _
from typing import Any, Optional, Dict

from sqlalchemy.ext.asyncio import async_sessionmaker
from financial_bot.repositories import get_user_by_id
from financial_bot.language import LANGUAGE


# class DbSessionMiddleware(BaseMiddleware):
#     async def __call__(
#         self,
#         handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
#         event: TelegramObject,
#         data: Dict[str, Any],
#     ) -> Any:
#         async with async_session() as session:
#             data["session"] = session  # Прокидываем сессию в хендлер
#             return await handler(event, data)


class SessionMiddleware(BaseMiddleware):

    def __init__(self, session_pool: async_sessionmaker):
        self.session_pool = session_pool

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:


        async with self.session_pool() as session:

            data["session"] = session


            return await handler(event, data)


class MyI18nMiddleware(I18nMiddleware):

    # Этот метод отвечает за выбор языка для каждого события
    async def get_locale(self, event: TelegramObject, data: Dict[str, Any]) -> str:
        session = data.get("session")  # Сессия из вашего предыдущего Middleware
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id

        # 1. Пытаемся взять из БД
            user = await get_user_by_id(session, user_id)
            if user and user.language_code:
                return user.language_code

            # 2. Если в БД нет, берем язык из Telegram или "en" по умолчанию
            return event.from_user.language_code

        return self.i18n.default_locale


# user = await get_user_by_id(session, event.from_user.id)
            #
            # if user and user.language_code:
            #     active_lang = user.language_code
            #
            # else:
            #     active_lang = event.from_user.language_code or "en"
            #
            # if active_lang not in LANGUAGE:
            #     active_lang = "en"
            #
            #
            # data['lp'] = LANGUAGE.get(active_lang, LANGUAGE['en'])