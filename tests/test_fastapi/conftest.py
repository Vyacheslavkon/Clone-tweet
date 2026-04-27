import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from application import models
from main import app


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
