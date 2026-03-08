from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application import models


async def test_like_delete(
    client: AsyncClient, test_session: AsyncSession, first_user, test_tweet_with_media
):

    headers = {"api-key": first_user.api_key}
    new_like = models.Likes(user_id=first_user.id, tweet_id=test_tweet_with_media.id)

    test_session.add(new_like)
    await test_session.flush()
    await test_session.refresh(new_like)

    response = await client.delete(
        f"/api/tweets/{test_tweet_with_media.id}/likes", headers=headers
    )

    query_like = select(models.Likes).where(
        models.Likes.user_id == first_user.id,
        models.Likes.tweet_id == test_tweet_with_media.id,
    )
    result = await test_session.execute(query_like)
    like = result.scalars().one_or_none()

    assert response.status_code == 200
    assert not like
