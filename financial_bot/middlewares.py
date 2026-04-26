from typing import Any, Awaitable, Callable, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.utils.i18n import I18nMiddleware
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio.session import AsyncSession

from financial_bot.repositories import get_user_by_id


class SessionMiddleware(BaseMiddleware):

    def __init__(self, session_pool: async_sessionmaker | AsyncSession):
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:

        if isinstance(self.session_pool, AsyncSession):
            data["session"] = self.session_pool

            return await handler(event, data)

        async with self.session_pool() as session:

            data["session"] = session

            return await handler(event, data)


class MyI18nMiddleware(I18nMiddleware):

    async def get_locale(self, event: TelegramObject, data: Dict[str, Any]) -> str:
        # session = data.get("session")
        session: Optional[AsyncSession] = data.get("session")

        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            user_id = event.from_user.id
            if session:
                user = await get_user_by_id(session, user_id)
                if user and user.language_code:
                    return str(user.language_code)

            return event.from_user.language_code or self.i18n.default_locale

        return str(self.i18n.default_locale)

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
