import os

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application import models


async def test_delete_tweet(
    client: AsyncClient, test_session: AsyncSession, test_tweet_with_media, add_user
):

    media_list = await test_tweet_with_media.awaitable_attrs.tweet_media_ids
    file_path = media_list[0].path

    headers = {"api-key": "test"}
    response = await client.delete(
        f"/api/tweets/{test_tweet_with_media.id}", headers=headers
    )

    query_tweet = select(models.Tweet).where(
        models.Tweet.id == test_tweet_with_media.id
    )
    result = await test_session.execute(query_tweet)
    tweet = result.scalars().one_or_none()

    query_media = select(models.Media).where(
        models.Media.tweet_id == test_tweet_with_media.id
    )
    result = await test_session.execute(query_media)
    media = result.scalars().all()

    assert response.status_code == 200
    assert not tweet
    assert os.path.exists(file_path) is False
    assert not media
