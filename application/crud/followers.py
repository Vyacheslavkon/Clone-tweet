from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from application.models import User,FollowLink


async def create_follow(session: AsyncSession, user: User, user_id: int):
    new_subscription = FollowLink(follower_id=user.id, followed_id=user_id)
    session.add(new_subscription)
    try:
        await session.commit()

    except IntegrityError as e:
        await session.rollback()

        raise


async def get_follow(session: AsyncSession, user: User, user_id: int) -> FollowLink | None:
    query = select(FollowLink).where(
        FollowLink.followed_id == user_id, FollowLink.follower_id == user.id
    )

    result = await session.execute(query)

    follow = result.scalars().one_or_none()

    return follow



async def del_follow(session: AsyncSession, follow: FollowLink):

    await session.delete(follow)

    await session.commit()

