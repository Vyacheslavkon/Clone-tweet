import asyncio
import os

import aiohttp
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from loguru import logger

_global_bot_session: AiohttpSession | None = None
_global_bot_instance: Bot | None = None


def get_shared_bot() -> Bot:

    global _global_bot_session, _global_bot_instance
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("The BOT_TOKEN environment variable is not set!")

    _global_bot_session = AiohttpSession()
    _global_bot_instance = Bot(
        token=token,
        session=_global_bot_session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    return _global_bot_instance  # noqa: PIE781


async def close_shared_bot() -> None:
    global _global_bot_session, _global_bot_instance
    session, _global_bot_session = _global_bot_session, None
    _global_bot_instance = None

    if session is None:
        return
    try:
        await session.close()
        logger.info("Shared Bot session closed.")
    except (RuntimeError, aiohttp.ClientError):
        logger.exception("Failed to close shared Bot session")