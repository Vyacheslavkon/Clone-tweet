from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def test_post_tweet(client: AsyncClient, test_session: AsyncSession, first_user):
    tweet_data = {"tweet_data": "data test."}
    headers = {"api-key": first_user.api_key}
    response = await client.post("/api/tweets", json=tweet_data, headers=headers)

    query_tweet = select(models.Tweet).where(
        models.Tweet.id == response.json()["tweet_id"]
    )
    result = await test_session.execute(query_tweet)
    tweet = result.scalars().one_or_none()
    assert tweet is not None

    answer = {"result": True, "tweet_id": tweet.id}
    data_create_tweet = tweet.tweet_data

    assert response.status_code == 201
    assert response.json() == answer
    assert tweet_data["tweet_data"] == data_create_tweet


async def test_update_media_with_create_tweet(
    client: AsyncClient, test_session: AsyncSession, first_user, test_tweet_with_media
):

    temp_path = "test_image.jpg"
    media = models.Media(path=temp_path, tweet_id=test_tweet_with_media.id)
    test_session.add(media)
    await test_session.flush()
    await test_session.refresh(media)

    data_for_tweet = {"tweet_data": "test data", "tweet_media_ids": [media.id]}

    headers = {"api-key": first_user.api_key}
    response = await client.post("/api/tweets", json=data_for_tweet, headers=headers)
    new_tweet_id = response.json()["tweet_id"]

    result = await test_session.execute(
        select(models.Media).where(models.Media.id == media.id)
    )
    updated_media = result.scalar_one()

    assert response.status_code == 201
    assert updated_media.tweet_id == new_tweet_id
