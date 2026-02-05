import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_users_me(client: AsyncClient, test_session: AsyncSession):
    headers = {"api_key": "test"}
    response = await client.get("/api/users/me", headers=headers)

    assert response.status_code == 200

