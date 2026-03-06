from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application import models


async def test_post_follower(client: AsyncClient, test_session: AsyncSession, add_user):

    headers = {"api-key": "super"}

    follower_user_test = models.User(name="Max", api_key="super")
    test_session.add(follower_user_test)
    await test_session.flush()
    await test_session.refresh(follower_user_test)

    response = await client.post(f"/api/users/{add_user.id}/follow", headers=headers)
    answer = {"result": True}

    followlink_query = select(models.FollowLink).where(
        models.FollowLink.followed_id == add_user.id
    )
    result = await test_session.execute(followlink_query)
    follow = result.scalars().one_or_none()

    assert response.status_code == 200
    assert follow
    assert response.json() == answer
