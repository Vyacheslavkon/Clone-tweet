from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def test_users_me(client: AsyncClient, test_session: AsyncSession, first_user):
    headers = {"api-key": "test"}
    response = await client.get("/api/users/me", headers=headers)

    info_user = {
        "result": True,
        "user": {
            "followers": [],
            "following": [],
            "id": first_user.id,
            "name": first_user.name,
        },
    }
    assert response.status_code == 200
    assert response.json() == info_user


async def test_invalid_api_key(
    client: AsyncClient, test_session: AsyncSession, first_user
):
    headers = {"api-key": "invalid"}
    response = await client.get("api/users/me", headers=headers)
    assert response.status_code == 404
