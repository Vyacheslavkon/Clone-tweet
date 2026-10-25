import os
from dataclasses import dataclass, field

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.utils.i18n import I18n, SimpleI18nMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from redis.asyncio import Redis

from core.config import TOKEN_BOT
from core.database import bot_engine, bot_session_maker
from financial_bot.handlers.adding_data import router_data
from financial_bot.handlers.ai_consultant import ai_router
from financial_bot.handlers.common import router
from financial_bot.handlers.del_transactions import router_del_transactions
from financial_bot.handlers.fallback import router_fallback
from financial_bot.handlers.history import history_rout
from financial_bot.handlers.reports import report_rout
from financial_bot.handlers.settings import settings_router
from financial_bot.handlers.transactions import router_tr
from financial_bot.middlewares import SessionMiddleware, MyI18nMiddleware, UserActivityMiddleware
from services.analysis_cache import FinancialCacheService
from services.scheduled import setup_scheduler


@dataclass
class Runtime:
    bot: Bot
    dp: Dispatcher
    scheduler: AsyncIOScheduler
    _redis_fsm: Redis = field(repr=False)
    _redis_cache: Redis = field(repr=False)
    _bot_session: AiohttpSession = field(repr=False)

    async def close(self) -> None:
        # каждый ресурс закрываем независимо, как в on_worker_shutdown
        for name, closer in (
            ("Redis FSM", self._redis_fsm.aclose),
            ("Redis cache", self._redis_cache.aclose),
            ("Bot HTTP session", self._bot_session.close),
            ("DB engine", bot_engine.dispose),
        ):
            try:
                await closer()
                logger.info("{name} closed", name=name)
            except Exception as e:  # noqa: PIE786 - shutdown must try every resource
                logger.error("Failed to close {name}: {error}", name=name, error=e)


def build_runtime() -> Runtime:
    redis_fsm = Redis(host="redis", port=6379, db=2, max_connections=20, decode_responses=True)
    redis_url = os.environ["ANALYSIS_CACHE_REDIS"]
    redis_cache = Redis.from_url(redis_url, decode_responses=True, max_connections=20)

    i18n = I18n(path="/application/financial_bot/locales", default_locale="en", domain="messages")

    bot_session = AiohttpSession()
    bot = Bot(
        token=TOKEN_BOT,
        session=bot_session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=RedisStorage(redis=redis_fsm))

    dp["admin_id"] = int(os.environ["ADMIN_ID"])
    dp["cache_service"] = FinancialCacheService(redis_client=redis_cache)

    dp.message.outer_middleware(SessionMiddleware(bot_session_maker))
    dp.callback_query.outer_middleware(SessionMiddleware(bot_session_maker))
    i18n_mw = MyI18nMiddleware(i18n=i18n)
    dp.message.outer_middleware(i18n_mw)
    dp.callback_query.outer_middleware(i18n_mw)
    dp.errors.middleware(SimpleI18nMiddleware(i18n))
    dp.update.outer_middleware(SimpleI18nMiddleware(i18n))
    dp.update.outer_middleware(UserActivityMiddleware())

    for r in (router, router_tr, router_data, report_rout, history_rout,
              ai_router, router_del_transactions, settings_router, router_fallback):
        dp.include_router(r)

    return Runtime(bot, dp, setup_scheduler(), redis_fsm, redis_cache, bot_session)