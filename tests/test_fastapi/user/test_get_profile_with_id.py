from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def test_get_profile_id(
    client: AsyncClient, test_session: AsyncSession, first_user, second_user
):

    headers = {"api-key": first_user.api_key}
    response = await client.get(f"/api/users/{second_user.id}", headers=headers)

    answer = {
        "result": True,
        "user": {
            "id": second_user.id,
            "name": second_user.name,
            "followers": [],
            "following": [{"id": first_user.id, "name": first_user.name}],
        },
    }
    assert response.status_code == 200
    assert response.json() == answer
