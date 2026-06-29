from datetime import datetime
from decimal import Decimal

from aiogram.utils.i18n import gettext as _
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from financial_bot.exceptions import UserNotFoundError
from financial_bot.models import Transactions, UserBot, TransactionItems
from financial_bot.schemas import AddData, CreateUser, Plan
from services.schemas import ReceiptAnalysisSchema, ReceiptListAnalysisSchema

async def create_user(session: AsyncSession, data: CreateUser):

    new_user = UserBot(
        tg_id=data.tg_id, first_name=data.first_name, language_code=data.language_code
    )

    session.add(new_user)
    await session.commit()
    logger.info("User {} created successfully.", data.first_name)

    return new_user


async def get_all_users(session: AsyncSession) -> list[UserBot]:

    query = select(UserBot).where(UserBot.is_active == True)
    result = await session.execute(query)

    return list(result.scalars().all())


async def get_user_by_id(session: AsyncSession, tg_id: int) -> UserBot | None:

    query = select(UserBot).where(UserBot.tg_id == tg_id)
    result = await session.execute(query)

    return result.scalars().one_or_none()


async def blocked_user(session: AsyncSession, user_tg_id: int):

    user = await get_user_by_id(session, user_tg_id)

    if user:
        user.is_active = False
        await session.commit()

    else:
        error_message = _(f"The user with the id {user_tg_id} was not found in the system.")
        logger.error(error_message)
        raise UserNotFoundError(error_message)


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


async def get_planned_goals(session: AsyncSession, tg_id: int) -> Plan:
    user = await get_user_by_id(session, tg_id)

    if not user:
        logger.warning("User with id {} not found", tg_id)
        return Plan()

    return Plan(
        monthly_budget=user.monthly_budget,
        budget_remind_percent=user.budget_remind_percent,
        savings_goal=user.savings_goal,
    )


async def get_report_period(
    session: AsyncSession, tg_id: int, date_start: datetime, date_end: datetime
) -> list:

    user = await get_user_by_id(session, tg_id)

    if user is not None:

        query = (
            select(
                Transactions.type,
                Transactions.category,
                func.sum(Transactions.amount).label("total"),
            )
            .where(
                Transactions.user_id == user.id,
                Transactions.created_at.between(date_start, date_end),
            )
            .group_by(Transactions.type, Transactions.category)
        )

        results = await session.execute(query)

        res = list(results.all())

    else:
        logger.warning("User with id {} not found", tg_id)

        res = []

    return res


# async def save_receipt_to_db(
#         session: AsyncSession,
#         user_id: int,
#         analysis_result: ReceiptListAnalysisSchema,
#         photo_url: str,
#         raw_text: str
# ):
#
#     for group in analysis_result.transactions:
#         db_transaction = Transactions(
#             user_id=user_id,
#             amount=group.amount,
#             category=group.category,
#             type="expense",
#             description=group.description,
#             text_check=raw_text
#         )
#         session.add(db_transaction)
#         await session.flush()  # Получаем id для One-to-Many
#
#         if group.items:
#             db_items = [
#                 TransactionItems(
#                     transaction_id=db_transaction.id,
#                     name=item.name,
#                     price=item.price,
#                     category=group.category
#                 )
#                 for item in group.items
#             ]
#             session.add_all(db_items)
#
#     await session.commit()

# test
async def save_receipt_to_db(
        session: AsyncSession,
        user_id: int,
        analysis_result: ReceiptListAnalysisSchema,
        photo_url: str,
        raw_text: str,
        batch_id: str
):

    for group in analysis_result.transactions:
        db_transaction = Transactions(
            user_id=user_id,
            amount=group.amount,
            category=group.category,
            type="expense",
            description=group.description,
            text_check=raw_text,
            batch_id=batch_id
        )
        session.add(db_transaction)
        await session.flush()  # Получаем id для One-to-Many

        if group.items:
            db_items = [
                TransactionItems(
                    transaction_id=db_transaction.id,
                    name=item.name,
                    price=item.price,
                    category=group.category
                )
                for item in group.items
            ]
            session.add_all(db_items)

    await session.commit()