from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application import models


async def test_delete_follow(
    client: AsyncClient, test_session: AsyncSession, first_user, second_user, follow
):

    headers = {"api-key": first_user.api_key}
    response = await client.delete(
        f"/api/users/{second_user.id}/follow", headers=headers
    )

    query_follow = select(models.FollowLink).where(
        models.FollowLink.follower_id == first_user.id,
        models.FollowLink.followed_id == second_user.id,
    )

    result = await test_session.execute(query_follow)

    follow = result.scalars().one_or_none()

    assert response.status_code == 200
    assert not follow
