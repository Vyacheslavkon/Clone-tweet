import os

import pytest
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool.impl import NullPool

from application import models
from application.database import Base, get_db
from application.routes import app

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
async def add_user(test_session: AsyncSession):

    new_user = models.User(api_key="test", name="test_user")

    test_session.add(new_user)
    await test_session.flush()
    await test_session.refresh(new_user)
    return new_user


@pytest.fixture
async def test_tweet_with_media(
    test_session: AsyncSession, client: AsyncClient, add_user
):
    temp_path = "test_image.jpg"
    with open(temp_path, "w") as f:
        f.write("test data")

    media = models.Media(path=temp_path)
    tweet = models.Tweet(
        user_id=add_user.id, tweet_media_ids=[media], tweet_data="test data"
    )

    test_session.add(tweet)
    await test_session.flush()
    await test_session.refresh(tweet)

    return tweet
