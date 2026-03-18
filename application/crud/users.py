from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.models import User

async def get_user_by_api_key(session: AsyncSession, api_key: str) -> User | None:

    query = select(User).where(User.api_key == api_key)

    result = await session.execute(query)

    return result.scalars().one_or_none()


async def get_user(session: AsyncSession, user: User) -> User:

    query = (select(User).where(User.id == user.id)
             .options(selectinload(User.followers),
                      selectinload(User.following)))

    result = await session.execute(query)

    return result.scalars().first()