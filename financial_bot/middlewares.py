from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from aiogram.types import Update
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


class LangSessionMiddleware(BaseMiddleware):

    def __init__(self, session_pool: async_sessionmaker):
        self.session_pool = session_pool

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:


        # 2. Достаем язык из вашей БД (или берем системный, если юзера нет)
        async with self.session_pool() as session:

            data["session"] = session

            user = await get_user_by_id(session, event.from_user.id)

            if user and user.language_code:
                active_lang = user.language_code

            else:
                active_lang = event.from_user.language_code or "en"

            if active_lang not in LANGUAGE:
                active_lang = "en"


            data['lp'] = LANGUAGE.get(active_lang, LANGUAGE['en'])

            return await handler(event, data)