import os
import asyncio
import aiohttp
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import DefaultBotProperties
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
    return _global_bot_instance


async def close_shared_bot():
    global _global_bot_session, _global_bot_instance

    if _global_bot_session:
        try:
            await _global_bot_session.close()
            logger.info("Shared Bot session closed successfully.")

        except asyncio.CancelledError:

            logger.warning("Bot session closure was cancelled by the runtime environment.")
            raise

        except (RuntimeError, aiohttp.ClientError) as err:

            logger.warning(
                "Expected networking error during Bot session closure: {error_type} - {msg}",
                error_type=type(err).__name__,
                msg=str(err)
            )

        except Exception as e:

            logger.error(
                "Unexpected critical error while closing shared bot session: {error}",
                error=e,
                exc_info=True
            )
        finally:

            _global_bot_session = None
            _global_bot_instance = None