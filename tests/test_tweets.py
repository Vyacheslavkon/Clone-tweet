import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_post_tweet(client: AsyncClient,  test_session: AsyncSession,
                          test_tweet_with_media, add_user):
    tweet_data = {"tweet_data": "data test."}
    headers = {"api-key": "test"}
    response = await client.post("/api/tweets", json=tweet_data, headers=headers)

    #answer = {"result": True, "tweet_id": test_tweet_with_media.id}
    answer = response.json()

    assert response.status_code == 201
    assert answer["tweet_id"] != test_tweet_with_media.id
    assert isinstance(answer["tweet_id"], int)
