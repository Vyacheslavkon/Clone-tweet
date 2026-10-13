from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import DATABASE_URL_DOCKER, ENGINE_KWARGS

_worker_engine: AsyncEngine | None = None
_worker_session_maker: async_sessionmaker | None = None


def get_isolated_session() -> AsyncSession:

    global _worker_engine, _worker_session_maker
    if _worker_engine is None:

        _worker_engine = create_async_engine(
            DATABASE_URL_DOCKER, pool_size=10, max_overflow=5, **ENGINE_KWARGS
        )
        _worker_session_maker = async_sessionmaker(
            bind=_worker_engine, expire_on_commit=False, class_=AsyncSession
        )

    if _worker_session_maker is None:
        raise RuntimeError("Worker session maker was not initialized properly!")

    return _worker_session_maker()


async def close_worker_db_engine() -> None:
    global _worker_engine, _worker_session_maker
    if _worker_engine is not None:
        await _worker_engine.dispose()
    _worker_engine = None
    _worker_session_maker = None
