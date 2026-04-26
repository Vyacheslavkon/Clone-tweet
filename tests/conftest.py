import os

import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool.impl import NullPool

from core.database import Base, get_db
from main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if TEST_DATABASE_URL is None:
    raise ValueError("TEST_DATABASE_URL is not set in environment variables")
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture(scope="function")
async def test_session():
    app.dependency_overrides.clear()

    async with test_engine.connect() as connection:

        transaction = await connection.begin()
        async with AsyncSession(bind=connection, expire_on_commit=False) as session:

            async def override_get_db():
                yield session

            app.dependency_overrides[get_db] = override_get_db
            yield session

            await session.close()

        await transaction.rollback()
        app.dependency_overrides.clear()


@pytest.fixture
async def test_redis():

    redis = Redis(host="test_redis", port=6379, db=3)
    yield redis
    await redis.flushdb()
    await redis.aclose()
