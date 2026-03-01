import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_post_like(
    client: AsyncClient, test_session: AsyncSession, add_user, test_tweet_with_media
):

    id = test_tweet_with_media.id
    headers = {"api-key": "test"}

    response = await client.post(f"/api/tweets/{id}/likes", headers=headers)
    answer = {"result": True}

    assert response.status_code == 201
    assert response.json() == answer


@pytest.mark.asyncio
async def no_valid_data(
    client: AsyncClient, test_session: AsyncSession, add_user, test_tweet_with_media
):

    id_no_valid = "test"
    headers = {"api-key": "test"}

    response = await client.post(f"/api/tweets/{id_no_valid}/likes", headers=headers)

    assert response.status_code == 422
