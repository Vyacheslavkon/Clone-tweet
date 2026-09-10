import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.utils.i18n import I18n, SimpleI18nMiddleware
from dotenv import load_dotenv
from redis.asyncio import Redis
from loguru import logger

from core.config import TOKEN_BOT
from core.database import bot_session_maker
from financial_bot.handlers.adding_data import router_data
from financial_bot.handlers.ai_consultant import ai_router
from financial_bot.handlers.common import router
from financial_bot.handlers.fallback import router_fallback
from financial_bot.handlers.history import history_rout
from financial_bot.handlers.reports import report_rout
from financial_bot.handlers.transactions import router_tr
from financial_bot.middlewares import (
    MyI18nMiddleware,
    SessionMiddleware,
    UserActivityMiddleware,
)
from financial_bot.tasks.scheduled import setup_scheduler
from services.analysis_cache import FinancialCacheService
from logger_config import setup_logging

redis_fsm = Redis(host="redis", port=6379, db=2,  max_connections=20, decode_responses=True)
storage = RedisStorage(redis=redis_fsm)
i18n = I18n(
    path="/application/financial_bot/locales", default_locale="en", domain="messages"
)

admin_id = int(os.getenv("ADMIN_ID"))

redis_url = os.getenv("ANALYSIS_CACHE_REDIS")
if not redis_url:
    raise ValueError("CRITICAL: ANALYSIS_CACHE_REDIS environment variable is not set!")


async def main():
    load_dotenv()
    setup_logging()
    bot_session = AiohttpSession()
    bot = Bot(token=TOKEN_BOT,
              session=bot_session,
              default=DefaultBotProperties(parse_mode=ParseMode.HTML)
              )
    dp = Dispatcher(storage=storage)
    session_pool = bot_session_maker
    scheduler = setup_scheduler(bot, session_pool, i18n)
    dp["admin_id"] = int(os.getenv("ADMIN_ID", 0))
    redis = Redis.from_url(
        url=redis_url,
        decode_responses=True,
        max_connections=20
    )
    cache_service = FinancialCacheService(redis_client=redis)
    dp["cache_service"] = cache_service
    dp.message.outer_middleware(SessionMiddleware(session_pool))
    dp.callback_query.outer_middleware(SessionMiddleware(session_pool))
    dp.errors.middleware(SimpleI18nMiddleware(i18n))
    dp.message.middleware(MyI18nMiddleware(i18n=i18n))
    dp.update.outer_middleware(SimpleI18nMiddleware(i18n))
    dp.update.outer_middleware(UserActivityMiddleware())
    dp.include_router(router)
    dp.include_router(router_tr)
    dp.include_router(router_data)
    dp.include_router(report_rout)
    dp.include_router(history_rout)
    dp.include_router(ai_router)
    dp.include_router(router_fallback)


    try:
        scheduler.start()
        await dp.start_polling(bot)

    except Exception as e:  # noqa
        logger.critical("Critical error in bot core execution: {error}", error=e, exc_info=True)

    finally:
        await redis_fsm.close()
        logger.info("Redis FSM client closed.")

        scheduler.shutdown()
        logger.info("Scheduler stopped.")

        await redis.aclose()
        logger.info("Redis cache client closed.")

        await bot_session.close()
        logger.info("Bot HTTP session closed.")



if __name__ == "__main__":
    asyncio.run(main())

