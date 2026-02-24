import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession




@pytest.mark.asyncio
async def test_users_me(client: AsyncClient, test_session: AsyncSession, add_user):
    headers = {"api-key": "test"}
    response = await client.get("/api/users/me", headers=headers)

    info_user = {
        "result": "true",
        "user": {"followers": [], "following": [], "id": add_user.id,
                        "name": add_user.name},
    }
    assert response.status_code == 200
    assert response.json() == info_user


@pytest.mark.asyncio
async def test_invalid_api_key(client: AsyncClient, test_session: AsyncSession,
                               add_user):
    headers = {"api-key": "invalid"}
    response = await client.get("api/users/me", headers=headers)
    print("ANSWER:", response.json())
    assert response.status_code == 404
