import logging
from typing import Optional, Type, Callable
from pydantic import BaseModel
import redis.asyncio as aioredis
from redis.exceptions import RedisError
from pydantic import ValidationError
from loguru import logger


# class AnalysisCacheService:
#     def __init__(self, redis_url: str):
#         """
#         Инициализирует асинхронное подключение к Redis.
#         decode_responses=True автоматически превращает bytes в строки Python.
#         """
#         self.redis = aioredis.from_url(redis_url, decode_responses=True)
#
#     @staticmethod
#     def _get_key(user_id: int, days: int) -> str:
#         """Внутренний хелпер для генерации уникального ключа кэша."""
#         return f"user:{user_id}:analysis:{days}"
#
#     async def get_cached_analysis(
#             self,
#             user_id: int,
#             days: int,
#             response_schema: Type[BaseModel]
#     ) -> Optional[BaseModel]:
#         """
#         Пытается получить и валидировать кэшированный отчет из Redis.
#         При несоответствии схемы (после рефакторинга) — безопасно удаляет старый кэш.
#         """
#         key = self._get_key(user_id, days)
#         try:
#             cached_json = await self.redis.get(key)
#             if not cached_json:
#                 return None
#
#             # Валидируем JSON-строку и собираем полноценный Pydantic-объект
#             return response_schema.model_validate_json(cached_json)
#
#
#         except ValidationError as val_err:
#
#             logger.warning(
#
#                 "Pydantic validation failed for cached user %s analysis. Invalidating cache. Error: %s",
#
#                 user_id, val_err
#
#             )
#
#             await self.redis.delete(key)
#
#             return None
#
#         except RedisError as redis_err:
#
#             logger.error(
#
#                 "Redis database error occurred while fetching cache for user %s: %s",
#
#                 user_id, redis_err
#
#             )
#
#             return None
#
#     async def set_analysis_cache(
#             self,
#             user_id: int,
#             days: int,
#             analysis_result: BaseModel,
#             expire_seconds: int = 86400
#     ) -> None:
#         """Сериализует Pydantic-модель в JSON и сохраняет в Redis (по умолчанию на 24 часа)."""
#         key = self._get_key(user_id, days)
#         try:
#             # model_dump_json() гарантирует идеальную сериализацию без багов типов
#             json_data = analysis_result.model_dump_json()
#             await self.redis.set(key, json_data, ex=expire_seconds)
#         except RedisError as redis_err:
#             logger.error("Failed to write analysis cache to Redis for user %s: %s", user_id, redis_err)
#
#     async def invalidate_user_cache(self, user_id: int) -> None:
#         """
#         Мгновенная инвалидация. Удаляет кэш недели и месяца при изменении баланса.
#         """
#         key_weekly = self._get_key(user_id, 7)
#         key_monthly = self._get_key(user_id, 30)
#         try:
#             # Асинхронно удаляем оба ключа за один запрос
#             await self.redis.delete(key_weekly, key_monthly)
#             logger.info("Successfully invalidated financial analysis cache for user %s", user_id)
#         except RedisError as redis_err:
#             logger.error("Failed to invalidate Redis cache for user %s: %s", user_id, redis_err)
#
#     async def close_connection(self) -> None:
#         """Безопасное закрытие пула соединений Redis (для завершения тасков)."""
#         await self.redis.close()


class AnalysisCacheService:
    def __init__(self, redis_url: str):
        """Конструктор только запоминает конфигурацию, это на 100% безопасно."""
        self.redis_url = redis_url
        self.client: Optional[aioredis.Redis] = None

    async def __aenter__(self):
        """Открывает изолированный пул сокетов при входе в контекст async with."""
        self.client = aioredis.from_url(self.redis_url, decode_responses=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Гарантированно и мгновенно закрывает пул сокетов при выходе из контекста."""
        if self.client:
            await self.client.close()

    @staticmethod
    def _get_key(user_id: int, days: int) -> str:
        return f"user:{user_id}:analysis:{days}"

    async def get_cached_analysis(
            self, user_id: int, days: int, response_schema: Type[BaseModel]
    ) -> Optional[BaseModel]:
        """Пытается получить и валидировать кэшированный отчет."""
        if not self.client:
            raise RuntimeError("Cache client is not initialized. Use 'async with'.")

        key = self._get_key(user_id, days)
        try:
            cached_json = await self.client.get(key)
            if not cached_json:
                return None

            return response_schema.model_validate_json(cached_json)

        except ValidationError as val_err:
            logger.warning("Pydantic validation failed for cached user %s analysis: %s", user_id, val_err)
            await self.client.delete(key)
            return None
        except RedisError as redis_err:
            logger.error("Redis error in get_cached_analysis for user %s: %s", user_id, redis_err)
            return None

    async def set_analysis_cache(
            self, user_id: int, days: int, analysis_result: BaseModel, expire_seconds: int = 86400
    ) -> None:
        """Сохраняет сериализованный Pydantic-отчет в Redis."""
        if not self.client:
            raise RuntimeError("Cache client is not initialized. Use 'async with'.")

        key = self._get_key(user_id, days)
        try:
            json_data = analysis_result.model_dump_json()
            await self.client.set(key, json_data, ex=expire_seconds)
        except RedisError as redis_err:
            logger.error("Failed to write analysis cache to Redis for user %s: %s", user_id, redis_err)

    async def invalidate_user_cache(self, user_id: int) -> None:
        """Мгновенное удаление кэша недели и месяца для пользователя."""
        if not self.client:
            raise RuntimeError("Cache client is not initialized. Use 'async with'.")

        key_weekly = self._get_key(user_id, 7)
        key_monthly = self._get_key(user_id, 30)
        try:
            await self.client.delete(key_weekly, key_monthly)
            logger.info("Successfully invalidated financial analysis cache for user %s", user_id)
        except RedisError as redis_err:
            logger.error("Failed to invalidate Redis cache for user %s: %s", user_id, redis_err)
