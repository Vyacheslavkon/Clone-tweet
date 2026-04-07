import os
import tempfile
import pytest
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool.impl import NullPool
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from aiogram import Dispatcher
from unittest.mock import AsyncMock

from application import models
from core.database import Base, get_db
from main import app
from financial_bot.middlewares import SessionMiddleware
from financial_bot.handlers.transactions import router_tr
from financial_bot.handlers.common import router

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if TEST_DATABASE_URL is None:
    raise ValueError("TEST_DATABASE_URL is not set in environment variables")
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)


@app.exception_handler(Exception)
async def debug_exception_handler(request, exc):
    import traceback

    traceback.print_exc()
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # original_lifespan_context = app.router.lifespan_context
    # app.router.lifespan_context = None

    yield

    # app.router.lifespan_context = original_lifespan_context
    # app.dependency_overrides = {}

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


@pytest.fixture(scope="function")
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def first_user(test_session: AsyncSession):

    new_user = models.User(api_key="test", name="test_user")

    test_session.add(new_user)
    await test_session.flush()
    await test_session.refresh(new_user)
    return new_user


@pytest.fixture
async def second_user(test_session: AsyncSession, first_user):
    new_user = models.User(
        api_key="user",
        name="second_user",
    )

    test_session.add(new_user)
    await test_session.flush()
    await test_session.refresh(new_user)

    follow = models.FollowLink(follower_id=new_user.id, followed_id=first_user.id)
    test_session.add(follow)
    await test_session.flush()
    await test_session.refresh(follow)

    return new_user


@pytest.fixture
async def test_tweet_with_media(
    test_session: AsyncSession, client: AsyncClient, first_user
):
    # temp_path = "test_image.jpg"
    # with open(temp_path, "w") as f:
    #     f.write("test data")
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(b"test data")
        temp_path = tmp.name

    media = models.Media(path=temp_path)
    tweet = models.Tweet(
        user_id=first_user.id, tweet_media_ids=[media], tweet_data="test data"
    )

    test_session.add(tweet)
    await test_session.flush()
    await test_session.refresh(tweet)

    yield tweet

    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
async def create_like(test_session: AsyncSession, test_tweet_with_media, second_user):

    new_like = models.Likes(user_id=second_user.id, tweet_id=test_tweet_with_media.id)

    test_session.add(new_like)
    await test_session.flush()
    await test_session.refresh(new_like)

    return new_like


@pytest.fixture
async def follow(test_session: AsyncSession, first_user, second_user):

    new_follow = models.FollowLink(
        follower_id=first_user.id, followed_id=second_user.id
    )
    test_session.add(new_follow)
    await test_session.flush()
    await test_session.refresh(new_follow)

    return new_follow


@pytest.fixture
async def test_redis():
    # Внутри Docker используем имя сервиса 'test_redis'
    redis = Redis(host='test_redis', port=6379, db=3)
    yield redis
    await redis.flushdb()
    await redis.close()


@pytest.fixture
async def test_dp(test_session, test_redis):
    # Используем RedisStorage в диспетчере
    storage = RedisStorage(redis=test_redis)
    dp = Dispatcher(storage=storage)

    # Подключаем Middleware и роутеры
    dp.update.middleware(SessionMiddleware(session_pool=test_session))
    dp.include_router(router)
    dp.include_router(router_tr)

    return dp


@pytest.fixture
def mock_bot():
    """Создает мок бота, который не делает реальных запросов"""
    bot = AsyncMock()
    bot.id = 12345678
    return bot