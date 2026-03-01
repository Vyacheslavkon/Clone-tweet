import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_tweet_feed(
    client: AsyncClient, test_session: AsyncSession, add_user, test_tweet_with_media
):

    headers = {"api-key": "test"}
    response = await client.get("/api/tweets", headers=headers)

    answer = {"result": True, "tweets": []}
    assert response.status_code == 200
    assert response.json() == answer
