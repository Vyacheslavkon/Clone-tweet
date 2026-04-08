import os
from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from application import models


async def test_delete_tweet(
    client: AsyncClient, test_session: AsyncSession, test_tweet_with_media, first_user
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


async def test_tweet_not_exist(
    client: AsyncClient, test_session: AsyncSession, first_user, test_tweet_with_media
):

    headers = {"api-key": first_user.api_key}
    no_ext_tweet = 345

    response = await client.delete(f"/api/tweets/{no_ext_tweet}", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot be deleted"


async def test_delete_tweet_integrity_error(
    client: AsyncClient, first_user, test_tweet_with_media
):

    with patch(
        "sqlalchemy.ext.asyncio.AsyncSession.commit",
        side_effect=IntegrityError(None, None, Exception("Database error")),
    ):
        headers = {"api-key": first_user.api_key}
        response = await client.delete(
            f"/api/tweets/{test_tweet_with_media.id}", headers=headers
        )

        assert response.status_code == 400
        assert "Entry does not exist." in response.json()["detail"]
