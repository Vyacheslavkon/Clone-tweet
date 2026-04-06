from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from financial_bot.schemas import CreateUser, AddTransaction
from financial_bot.models import UserBot, Transactions

async def create_user(session: AsyncSession, data: CreateUser):

    new_user = UserBot(
        tg_id=data.tg_id,
        first_name=data.first_name,
        language_code=data.language_code
    )

    session.add(new_user)
    await session.commit()
    logger.info("User {} created successfully.", data.first_name)

async def get_user_by_id(session: AsyncSession, tg_id: int) -> UserBot | None:

    query = select(UserBot).where(UserBot.tg_id == tg_id)
    result = await session.execute(query)

    return result.scalars().one_or_none()



async def add_transaction(session: AsyncSession, data: dict):


    transaction = Transactions(**data)
    session.add(transaction)
    await session.commit()
