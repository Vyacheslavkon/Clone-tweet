from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application import models


async def test_post_like(
    client: AsyncClient, test_session: AsyncSession, first_user, test_tweet_with_media
):

    id = test_tweet_with_media.id
    headers = {"api-key": "test"}

    response = await client.post(f"/api/tweets/{id}/likes", headers=headers)
    answer = {"result": True}

    query_like = select(models.Likes).where(
        models.Likes.user_id == first_user.id,
        models.Likes.tweet_id == test_tweet_with_media.id,
    )
    result = await test_session.execute(query_like)
    like = result.scalars().one_or_none()

    assert response.status_code == 200
    assert response.json() == answer
    assert like


async def test_like_exist(
    test_session: AsyncSession,
    client: AsyncClient,
    test_tweet_with_media,
    second_user,
    create_like,
):

    test_session.expunge_all()

    headers = {"api-key": second_user.api_key}

    response = await client.post(
        f"/api/tweets/{test_tweet_with_media.id}/likes", headers=headers
    )

    assert response.status_code == 400


async def no_valid_data(
    client: AsyncClient, test_session: AsyncSession, first_user, test_tweet_with_media
):

    id_no_valid = "test"
    headers = {"api-key": first_user.api_key}

    response = await client.post(f"/api/tweets/{id_no_valid}/likes", headers=headers)

    assert response.status_code == 422


async def test_like_non_existent_tweet(client: AsyncClient, first_user):

    non_existent_id = 999999
    headers = {"api-key": first_user.api_key}

    response = await client.post(
        f"/api/tweets/{non_existent_id}/likes", headers=headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Tweet not found"
