from sqlalchemy.exc import IntegrityError, MissingGreenlet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.models import User, Likes



async def create_like(session: AsyncSession, user: User, tweet_id: int):

    new_like = Likes(user_id=user.id, tweet_id=tweet_id)
    session.add(new_like)

    try:
        await session.commit()

    except (IntegrityError, MissingGreenlet):
        await session.rollback()
        raise


async  def get_like(session: AsyncSession, user: User, tweet_id: int) -> Likes | None:

    query = select(Likes).where(
        Likes.user_id == user.id, Likes.tweet_id == tweet_id
    )
    result = await session.execute(query)
    like = result.scalars().one_or_none()

    return like



async def del_like(session: AsyncSession, like: Likes):

    await session.delete(like)

    try:
        await session.commit()

    except IntegrityError:
        await session.rollback()

        raise

