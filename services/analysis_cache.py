import logging
from typing import Optional, Type, Callable
import os
from pydantic import BaseModel
import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import RedisError
from pydantic import ValidationError
from loguru import logger
from typing import Type, TypeVar, Optional

T = TypeVar("T", bound=BaseModel)

red_url = os.getenv("ANALYSIS_CACHE_REDIS")


class FinancialCacheService:
    def __init__(self, redis_client: Redis):

        self.client = redis_client

    @staticmethod
    def _get_key(user_id: int, days: int) -> str:
        return f"cache:fin_analysis:user:{user_id}:days:{days}"

    async def get_cached_analysis(
        self, user_id: int, days: int, response_schema: Type[T]
    ) -> Optional[T]:
        key = self._get_key(user_id, days)
        try:
            cached_json = await self.client.get(key)
            if not cached_json:
                return None

            return response_schema.model_validate_json(cached_json)

        except ValidationError as val_err:
            logger.warning(
                "Pydantic validation failed for cached user %s analysis. Invalidating key %s: %s",
                user_id, key, val_err
            )
            # Безопасное удаление: защита от падения Redis во время удаления битого кэша
            try:
                await self.client.delete(key)
            except RedisError as del_err:
                logger.error("Failed to delete corrupted cache key %s: %s", key, del_err)
            return None

        except RedisError as redis_err:
            logger.error("Redis read error in get_cached_analysis for user %s: %s", user_id, redis_err)
            return None

    async def set_analysis_cache(
        self,
        user_id: int,
        days: int,
        analysis_result: BaseModel,
        expire_seconds: int = 86400
    ) -> None:
        key = self._get_key(user_id, days)
        try:
            json_data = analysis_result.model_dump_json()
            await self.client.set(key, json_data, ex=expire_seconds)
        except RedisError as redis_err:
            logger.error("Failed to write analysis cache to Redis for user %s: %s", user_id, redis_err)

    async def invalidate_user_cache(self, user_id: int, periods: tuple[int, ...] = (7, 30)) -> None:

        keys = [self._get_key(user_id, days) for days in periods]
        try:
            async with self.client.pipeline(transaction=True) as pipe:

                pipe.delete(*keys) # type: ignore[unused-awaitable]
                await pipe.execute()
            logger.info("Successfully invalidated cache keys %s for user %s", keys, user_id)
        except RedisError as redis_err:
            logger.error("Failed to invalidate Redis cache for user %s: %s", user_id, redis_err)