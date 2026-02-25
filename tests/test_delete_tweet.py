import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_delete_tweet(
    client: AsyncClient, test_session: AsyncSession, test_tweet_with_media, add_user
):
    headers = {"api-key": "test"}
    response = await client.delete(
        f"/api/tweets/{test_tweet_with_media.id}", headers=headers
    )

    assert response.status_code == 200
