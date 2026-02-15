import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_users_me(client: AsyncClient, test_session: AsyncSession):
    headers = {"api-key": "test"}
    response = await client.get("/api/users/me", headers=headers)

    info_user = {
        "result": "true",
        "user": {"followers": [], "following": [], "id": 1, "name": "test_user"},
    }
    assert response.status_code == 200
    assert response.json() == info_user


@pytest.mark.asyncio
async def test_invalid_api_key(client: AsyncClient, test_session: AsyncSession):
    headers = {"api-key": "invalid"}
    response = await client.get("api/users/me", headers=headers)

    assert response.status_code == 404
