from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application import models


async def test_post_like(
    client: AsyncClient, test_session: AsyncSession, add_user, test_tweet_with_media
):

    id = test_tweet_with_media.id
    headers = {"api-key": "test"}

    response = await client.post(f"/api/tweets/{id}/likes", headers=headers)
    answer = {"result": True}

    query_like = select(models.Likes).where(
        models.Likes.user_id == add_user.id,
        models.Likes.tweet_id == test_tweet_with_media.id,
    )
    result = await test_session.execute(query_like)
    like = result.scalars().one_or_none()

    assert response.status_code == 200
    assert response.json() == answer
    assert like


async def no_valid_data(
    client: AsyncClient, test_session: AsyncSession, add_user, test_tweet_with_media
):

    id_no_valid = "test"
    headers = {"api-key": "test"}

    response = await client.post(f"/api/tweets/{id_no_valid}/likes", headers=headers)

    assert response.status_code == 422
