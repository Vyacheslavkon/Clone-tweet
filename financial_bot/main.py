import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.utils.i18n import I18n, SimpleI18nMiddleware
from dotenv import load_dotenv
from redis.asyncio import Redis

from core.config import TOKEN_BOT
from core.database import async_session
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

redis_fsm = Redis(host="redis", port=6379, db=2)
storage = RedisStorage(redis=redis_fsm)
i18n = I18n(
    path="/application/financial_bot/locales", default_locale="en", domain="messages"
)

redis_url = os.getenv("ANALYSIS_CACHE_REDIS")
if not redis_url:
    raise ValueError("CRITICAL: ANALYSIS_CACHE_REDIS environment variable is not set!")


async def main():
    load_dotenv()
    setup_logging()
    bot = Bot(token=TOKEN_BOT)
    dp = Dispatcher(storage=storage)
    # await bot.delete_webhook(drop_pending_updates=True)
    session_pool = async_session
    scheduler = setup_scheduler(bot, session_pool, i18n)
    dp["admin_id"] = int(os.getenv("ADMIN_ID", 0))
    redis = Redis.from_url(
        url=redis_url,
        decode_responses=True,
        max_connections=20
    )
    cache_service = FinancialCacheService(redis_client=redis)
    dp["cache_service"] = cache_service
    # ai_service = AIService(
    #         api_key=settings.OPENAI_API_KEY,
    #         base_url=settings.OPENAI_BASE_URL,
    #         model="gpt-4o-mini"
    #     )
    # dp["ai_service"] = ai_service
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

    finally:
        await redis_fsm.close()
        scheduler.shutdown()
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
