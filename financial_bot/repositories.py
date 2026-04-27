from decimal import Decimal

from aiogram.utils.i18n import gettext as _
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from financial_bot.exceptions import UserNotFoundError
from financial_bot.models import Transactions, UserBot
from financial_bot.schemas import (
    AddData,
    CreateUser,
)


async def create_user(session: AsyncSession, data: CreateUser):

    new_user = UserBot(
        tg_id=data.tg_id, first_name=data.first_name, language_code=data.language_code
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


async def add_data_for_user(session: AsyncSession, obj_data: AddData, tg_id: int):

    user = await get_user_by_id(session, tg_id)

    if not user:
        error_message = _(f"The user with the id {tg_id} was not found in the system.")
        logger.error(error_message)
        raise UserNotFoundError(error_message)

    update_data = obj_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():

        setattr(user, key, value)

    await session.commit()


async def get_monthly_budget(session: AsyncSession, tg_id: int) -> Decimal | None:

    user = await get_user_by_id(session, tg_id)

    if user is not None:
        budget = user.monthly_budget
    else:
        logger.warning("User with id {} not found", tg_id)
        budget = None

    return budget


async def get_limit_expense(session: AsyncSession, tg_id: int) -> int | None:

    user = await get_user_by_id(session, tg_id)

    if user is not None:
        limit_expense = user.budget_remind_percent
    else:
        logger.warning("User with id {} not found", tg_id)
        limit_expense = None

    return limit_expense


async def get_saved_goal(session: AsyncSession, tg_id: int) -> Decimal | None:

    user = await get_user_by_id(session, tg_id)

    if user is not None:

        saved_goal = user.savings_goal

    else:

        logger.warning("User with id {} not found", tg_id)
        saved_goal = None

    return saved_goal
