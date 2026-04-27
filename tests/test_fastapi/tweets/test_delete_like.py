from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from application import models


async def test_like_delete(
    client: AsyncClient,
    test_session: AsyncSession,
    second_user,
    test_tweet_with_media,
    create_like,
):

    headers = {"api-key": second_user.api_key}
    response = await client.delete(
        f"/api/tweets/{test_tweet_with_media.id}/likes", headers=headers
    )

    query_like = select(models.Likes).where(
        models.Likes.user_id == second_user.id,
        models.Likes.tweet_id == test_tweet_with_media.id,
    )
    result = await test_session.execute(query_like)
    like = result.scalars().one_or_none()

    answer = {"result": True}

    assert response.status_code == 200
    assert not like
    assert response.json() == answer


async def test_like_not_exist(
    client: AsyncClient,
    test_session: AsyncSession,
    test_tweet_with_media,
    second_user,
    create_like,
):

    headers = {"api-key": second_user.api_key}
    no_exist_tweet = 345
    response = await client.delete(
        f"/api/tweets/{no_exist_tweet}/likes", headers=headers
    )

    answer = "Entry does not exist."

    assert response.status_code == 404
    assert response.json()["detail"] == answer


async def test_delete_like_integrity_error(
    client: AsyncClient, second_user, create_like
):

    with patch(
        "sqlalchemy.ext.asyncio.AsyncSession.commit",
        side_effect=IntegrityError(None, None, Exception("Database error")),
    ):
        headers = {"api-key": second_user.api_key}
        response = await client.delete(
            f"/api/tweets/{create_like.tweet_id}/likes", headers=headers
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Unable to delete object."
