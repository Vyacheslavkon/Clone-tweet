import time
from typing import Any, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update
from aiogram.utils.i18n import I18nMiddleware
from loguru import logger
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from financial_bot.repositories import get_user_by_id


class SessionMiddleware(BaseMiddleware):
    def __init__(self, session_pool: async_sessionmaker | AsyncSession | None = None):
        self.session_pool = session_pool

    async def __call__(self, handler, event, data):
        current_pool = data.get("session_pool") or self.session_pool

        if not current_pool:
            raise ValueError(
                "Database session pool is not configured in middleware or workflow data!"
            )

        if isinstance(current_pool, AsyncSession):
            # Test path: the session and its rollback are managed externally via
            # a savepoint transaction in the test_session fixture. In production,
            # an AsyncSession never reaches this point directly.
            data["session"] = current_pool
            return await handler(event, data)

        async with current_pool() as session:
            data["session"] = session
            try:
                return await handler(event, data)
            except Exception as e:
                logger.warning(
                    "Rolling back session due to exception in handler: {error}", error=e
                )

                try:
                    await session.rollback()
                except SQLAlchemyError as rollback_err:
                    logger.error("Rollback itself failed: {error}", error=rollback_err)
                raise


class MyI18nMiddleware(I18nMiddleware):

    async def get_locale(self, event: TelegramObject, data: Dict[str, Any]) -> str:

        session: Optional[AsyncSession] = data.get("session")

        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            user_id = event.from_user.id
            if session:
                user = await get_user_by_id(session, user_id)
                if user and user.language_code:
                    return str(user.language_code)

            return event.from_user.language_code or self.i18n.default_locale

        return str(self.i18n.default_locale)


class UserActivityMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict[str, Any]):
        user = data.get("event_from_user")
        user_id = user.id if user else "unknown"
        username = f"(@{user.username})" if user and user.username else ""

        action = "Non-Update event"
        if isinstance(event, Update):
            if event.message:
                payload = (
                    event.message.text
                    if event.message.text
                    else f"[{event.message.content_type}]"
                )
                action = f"Msg: {payload}"
            elif event.callback_query:
                action = f"CB: {event.callback_query.data}"
            elif event.inline_query:
                action = f"Inline: {event.inline_query.query}"
            else:
                action = "Other update type"

        start_time = time.time()
        try:
            result = await handler(event, data)
        finally:
            duration = time.time() - start_time
            logger.info(
                "User: {user_id} | Username: {username} | "
                "Action: {action} | Time: {duration:.3f}s",
                user_id=user_id,
                username=username,
                action=action,
                duration=duration,
            )

        return result
