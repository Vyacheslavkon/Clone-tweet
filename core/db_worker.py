# services/worker_resources.py (или financial_bot/core/db_worker.py) — использует ТОЛЬКО Celery
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from core.config import DATABASE_URL_DOCKER, ENGINE_KWARGS

_worker_engine: AsyncEngine | None = None
_worker_session_maker: async_sessionmaker | None = None


def get_isolated_session() -> AsyncSession:
    """Ленивая фабрика сессий для Celery worker. Engine создаётся один раз
    при первом реальном вызове таска (после форка, внутри worker_loop),
    а не при импорте модуля."""
    global _worker_engine, _worker_session_maker
    if _worker_engine is None:
        _worker_engine = create_async_engine(
            DATABASE_URL_DOCKER, pool_size=10, max_overflow=5, **ENGINE_KWARGS
        )
        _worker_session_maker = async_sessionmaker(bind=_worker_engine, expire_on_commit=False, class_=AsyncSession)
    return _worker_session_maker()


async def close_worker_db_engine() -> None:
    global _worker_engine, _worker_session_maker
    if _worker_engine is not None:
        await _worker_engine.dispose()
    _worker_engine = None
    _worker_session_maker = None