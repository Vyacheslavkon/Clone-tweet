from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from application import  models

async def test_post_tweet(
    client: AsyncClient, test_session: AsyncSession, test_tweet_with_media, add_user
):
    tweet_data = {"tweet_data": "data test."}
    headers = {"api-key": "test"}
    response = await client.post("/api/tweets", json=tweet_data, headers=headers)

    answer = response.json()

    query_tweet = select(models.Tweet).where(models.Tweet.id == answer["tweet_id"])
    result = await test_session.execute(query_tweet)
    tweet = result.scalars().one_or_none()

    assert response.status_code == 201
    assert answer["tweet_id"] != test_tweet_with_media.id
    assert isinstance(answer["tweet_id"], int)
    assert tweet