import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_post_tweet(client: AsyncClient, test_session: AsyncSession):
    tweet_data = {"tweet_data": "data test."}
    headers = {"api-key": "test"}
    response = await client.post("/api/tweets", json=tweet_data, headers=headers)

    answer = {
        "result": True,
        "tweet_id": 1
    }

    assert response.status_code == 201
    assert response.json() == answer