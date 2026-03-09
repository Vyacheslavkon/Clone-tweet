from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application import models


async def test_post_follower(
    client: AsyncClient, test_session: AsyncSession, first_user, second_user
):


    headers = {"api-key": first_user.api_key}

    response = await client.post(f"/api/users/{second_user.id}/follow", headers=headers)
    answer = {"result": True}

    followlink_query = select(models.FollowLink).where(
        models.FollowLink.followed_id == second_user.id
    )
    result = await test_session.execute(followlink_query)
    follow = result.scalars().one_or_none()

    assert response.status_code == 200
    assert follow
    assert response.json() == answer


async def test_no_followed(client: AsyncClient, test_session: AsyncSession,
                           first_user, second_user):

    headers = {"api-key": first_user.api_key}
    non_existent_id = 138

    response = await client.post(f"/api/users/{non_existent_id}/follow", headers=headers)

    answer = "Target user not found."

    assert response.status_code == 404
    assert response.json()["detail"] == answer


async def test_not_unique(client: AsyncClient, test_session: AsyncSession, first_user, second_user):

    headers = {"api-key": second_user.api_key}

    response = await client.post(f"/api/users/{first_user.id}/follow", headers=headers)

    answer = "Already following."

    assert response.status_code == 400
    assert response.json()["detail"] == answer