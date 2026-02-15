import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from application import models
from application.database import Base, get_db
from application.routes import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if TEST_DATABASE_URL is None:
    raise ValueError("DATABASE_URL_DOCKER is not set in environment variables")
test_engine = create_async_engine(TEST_DATABASE_URL, echo=True)

TestingSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture(scope="session")
def event_loop():
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# @pytest.fixture(scope='function')
# async def test_session():
#     async with TestingSessionLocal() as session:
#         yield session


@pytest.fixture(scope="function")
async def test_session():
    # Используем соединение, чтобы обернуть всё в одну транзакцию
    async with test_engine.connect() as connection:
        # Начинаем транзакцию
        transaction = await connection.begin()
        async with AsyncSession(bind=connection, expire_on_commit=False) as session:
            yield session
        # Откатываем изменения после каждого теста (БД всегда чистая!)
        await transaction.rollback()


@pytest.fixture(scope="function")
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.dependency_overrides[get_db] = override_get_db

    # original_lifespan_context = app.router.lifespan_context
    # app.router.lifespan_context = None

    yield

    # app.router.lifespan_context = original_lifespan_context
    app.dependency_overrides = {}

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="session", autouse=True)
async def add_user(setup_test_db):
    async with TestingSessionLocal() as session:
        async with session.begin():
            new_user = models.User(api_key="test", name="test_user")

            session.add(new_user)
