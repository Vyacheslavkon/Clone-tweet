from datetime import datetime, timedelta, timezone, time
from decimal import Decimal

from aiogram.utils.i18n import gettext as _
from loguru import logger
from sqlalchemy import delete, func, select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from financial_bot.exceptions import UserNotFoundError
from financial_bot.models import TransactionItems, Transactions, UserBot
from financial_bot.schemas import AddData, CreateUser, Plan
from services.schemas import ReceiptListAnalysisSchema


async def create_user(session: AsyncSession, data: CreateUser):

    new_user = UserBot(
        tg_id=data.tg_id, first_name=data.first_name, language_code=data.language_code
    )

    session.add(new_user)
    await session.commit()
    logger.info("User {} created successfully.", data.first_name)

    return new_user


async def get_all_users(session: AsyncSession) -> list[UserBot]:

    query = select(UserBot).where(UserBot.is_active)  # delete is_active == true
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
        error_message = _(
            f"The user with the id {user_tg_id} was not found in the system."
        )
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


async def save_receipt_to_db(
    session: AsyncSession,
    user_id: int,
    analysis_result: ReceiptListAnalysisSchema,
    raw_text: str,
    batch_id: str,
    photo_url: str | None = None,
):
    try:
        for group in analysis_result.transactions:
            db_transaction = Transactions(
                user_id=user_id,
                amount=group.amount,
                category=group.category,
                type=group.type,
                description=group.description,
                text_check=raw_text,
                batch_id=batch_id,
            )
            session.add(db_transaction)
            await session.flush()  # Получаем id для One-to-Many

            if group.type == "expense" and group.items:
                db_items = [
                    TransactionItems(
                        transaction_id=db_transaction.id,
                        name=item.name,
                        price=item.price,
                        category=group.category,
                    )
                    for item in group.items
                ]
                session.add_all(db_items)

        await session.commit()

    except Exception as e:  # noqa: PIE786

        await session.rollback()
        # logger.error(f"Error saving batch {batch_id} to DB: {e}", exc_info=True)
        logger.error(
            "Error saving batch {batch_id} to DB: {error}",
            batch_id=batch_id,
            error=str(e),
            exc_info=True,
        )


async def delete_check(session: AsyncSession, batch_id: str):
    stmt_select = select(Transactions).where(Transactions.batch_id == batch_id)
    list_transactions = await session.execute(stmt_select)

    # if len(list_transactions.all()) > 0:
    if list_transactions.scalar() is not None:
        stmt = delete(Transactions).where(Transactions.batch_id == batch_id)
        await session.execute(stmt)
        await session.commit()
        return True

    else:
        return False


async def get_test_user_expense_summary(session: AsyncSession, user_id: int, days: int) -> dict:


    now = datetime.now(timezone.utc)
    end_date = datetime.combine(now.date(), time.max).replace(tzinfo=timezone.utc)



    if days == 7:
        start_of_week = now.date() - timedelta(days=now.weekday())
        start_date = datetime.combine(start_of_week, time.min)

    elif days == 30:
        start_of_month = now.date().replace(day=1)
        start_date = datetime.combine(start_of_month, time.min)


    else:

        start_date = datetime.combine(now.date() - timedelta(days=days), time.min).replace(tzinfo=timezone.utc)

    start_date = start_date.replace(tzinfo=timezone.utc)


    total_stmt = (
        select(
            func.sum(Transactions.amount).label("total_amount"),
            func.count(Transactions.id).label("total_count")
        )
        .where(Transactions.user_id == user_id, Transactions.created_at.between(start_date, end_date))
    )
    total_res = await session.execute(total_stmt)
    total_data = total_res.first()

    if not total_data or total_data.total_amount is None:
        return {}

    cat_stmt = (
        select(
            Transactions.category,
            func.sum(Transactions.amount).label("cat_amount"),
            func.count(Transactions.id).label("cat_count")
        )
        .where(Transactions.user_id == user_id, Transactions.created_at.between(start_date, end_date))
        .group_by(Transactions.category)
        .order_by(func.sum(Transactions.amount).desc())
    )
    cat_res = await session.execute(cat_stmt)

    categories = [
        {
            "category": row.category,
            "amount": float(row.cat_amount),
            "count": row.cat_count
        }
        for row in cat_res.all()
    ]


    items_stmt = (
        select(
            TransactionItems.name,
            func.sum(TransactionItems.price).label("item_total_amount"),
            func.count(TransactionItems.id).label("item_count"),
            Transactions.category.label("associated_category")
        )
        .join(Transactions, TransactionItems.transaction_id == Transactions.id)
        .where(Transactions.user_id == user_id, Transactions.created_at.between(start_date, end_date))
        .group_by(TransactionItems.name, Transactions.category)
        .order_by(func.sum(TransactionItems.price).desc())
        .limit(10)
    )
    items_res = await session.execute(items_stmt)

    top_items = [
        {
            "name": row.name,
            "total_amount": float(row.item_total_amount),
            "count": row.item_count,
            "category": row.associated_category
        }
        for row in items_res.all()
    ]

    return {
        "total_amount": float(total_data.total_amount),
        "total_count": total_data.total_count,
        "categories": categories,  # Из старого запроса
        "top_items": top_items,  # Наша конкретика!
        "days_period": days
    }


async def get_user_expense_summary(session: AsyncSession, user_id: int, days: int) -> dict:
    days = int(days)

    now = datetime.now(timezone.utc)
    end_date = now

    if days == 7:
        start_of_week = now.date() - timedelta(days=now.weekday())
        start_date = datetime.combine(start_of_week, time.min, tzinfo=timezone.utc)
        actual_days = (end_date.date() - start_of_week).days + 1

    elif days == 30:
        start_of_month = now.date().replace(day=1)
        start_date = datetime.combine(start_of_month, time.min, tzinfo=timezone.utc)
        actual_days = (end_date.date() - start_of_month).days + 1

    else:
        start_date = datetime.combine(now.date() - timedelta(days=days), time.min, tzinfo=timezone.utc)
        actual_days = days

    total_stmt = select(
        func.coalesce(func.sum(Transactions.amount), 0).label("total_amount"),
        func.count(Transactions.id).label("total_count")
    ).where(
        Transactions.user_id == user_id,
        Transactions.type == "expense",
        Transactions.created_at >= start_date,
        Transactions.created_at < end_date
    )

    total_res = await session.execute(total_stmt)
    row = total_res.fetchone()

    if not row or row.total_count == 0:
        return {}

    db_total_amount = float(row.total_amount)
    db_total_count = row.total_count

    cat_stmt = select(
        Transactions.category,
        func.sum(Transactions.amount).label("cat_amount"),
        func.count(Transactions.id).label("cat_count")
    ).where(
        Transactions.user_id == user_id,
        Transactions.type == "expense",  # Фильтр только расходов
        Transactions.created_at >= start_date,
        Transactions.created_at < end_date
    ).group_by(Transactions.category).order_by(func.sum(Transactions.amount).desc())

    cat_res = await session.execute(cat_stmt)
    categories = [
        {"category": r.category, "amount": float(r.cat_amount), "count": r.cat_count}
        for r in cat_res.all()
    ]

    if days == 7:

        items_stmt = (
            select(
                TransactionItems.name,
                TransactionItems.price.label("item_amount"),
                Transactions.category.label("associated_category"),
                Transactions.created_at.label("date")
            )
            .join(Transactions, TransactionItems.transaction_id == Transactions.id)
            .where(
                Transactions.user_id == user_id,
                Transactions.type == "expense",
                Transactions.created_at >= start_date,
                Transactions.created_at < end_date
            )
            .order_by(desc(TransactionItems.price))
            .limit(30)
        )
    else:

        items_stmt = (
            select(
                TransactionItems.name,
                TransactionItems.price.label("item_amount"),
                Transactions.category.label("associated_category"),
                Transactions.created_at.label("date")
            )
            .join(Transactions, TransactionItems.transaction_id == Transactions.id)
            .where(
                Transactions.user_id == user_id,
                Transactions.type == "expense",
                Transactions.created_at >= start_date,
                Transactions.created_at < end_date
            )
            .order_by(Transactions.created_at.desc())
        )

    items_res = await session.execute(items_stmt)

    top_items = [
        {
            "name": r.name,
            "total_amount": float(r.item_amount),  # Имя поля строго как в label() выше
            "category": r.associated_category,
            "date": r.date.strftime("%Y-%m-%d")
        }
        for r in items_res.all()
    ]

    return {
        "total_amount": round(db_total_amount, 2),
        "total_count": db_total_count,
        "categories": categories,
        "top_items": top_items,
        "days_period": actual_days
    }


async def get_user_financial_summary(
    session: AsyncSession,
    user_id: int,
    days: int,
    user_bot: UserBot
) -> dict:
    days = int(days)

    now = datetime.now(timezone.utc)
    end_date = now

    if days == 7:
        start_of_week = now.date() - timedelta(days=now.weekday())
        start_date = datetime.combine(start_of_week, time.min, tzinfo=timezone.utc)
        actual_days = (end_date.date() - start_of_week).days + 1

    elif days == 30:
        start_of_month = now.date().replace(day=1)
        start_date = datetime.combine(start_of_month, time.min, tzinfo=timezone.utc)
        actual_days = (end_date.date() - start_of_month).days + 1

    else:
        start_date = datetime.combine(now.date() - timedelta(days=days), time.min, tzinfo=timezone.utc)
        actual_days = days


    total_stmt = select(
        func.coalesce(func.sum(Transactions.amount), 0).label("total_amount"),
        func.count(Transactions.id).label("total_count")
    ).where(
        Transactions.user_id == user_id,
        Transactions.type == "expense",
        Transactions.created_at >= start_date,
        Transactions.created_at < end_date
    )


    total_res = await session.execute(total_stmt)
    row = total_res.fetchone()


    db_total_amount = float(row.total_amount) if row else 0.0
    db_total_count = row.total_count if row else 0


    income_stmt = select(
        func.coalesce(func.sum(Transactions.amount), 0).label("total_income")
    ).where(
        Transactions.user_id == user_id,
        Transactions.type == "income",
        Transactions.created_at >= start_date,
        Transactions.created_at < end_date
    )
    income_res = await session.execute(income_stmt)
    db_total_income = float(income_res.scalar_one_or_none() or 0.0)


    cat_stmt = select(
        Transactions.category,
        func.sum(Transactions.amount).label("cat_amount"),
        func.count(Transactions.id).label("cat_count")
    ).where(
        Transactions.user_id == user_id,
        Transactions.type == "expense",
        Transactions.created_at >= start_date,
        Transactions.created_at < end_date
    ).group_by(Transactions.category).order_by(func.sum(Transactions.amount).desc())


    cat_res = await session.execute(cat_stmt)
    categories = [
        {"category": r.category, "amount": float(r.cat_amount), "count": r.cat_count}
        for r in cat_res.all()
    ]


    if days == 7:
        items_stmt = (
            select(
                TransactionItems.name,
                TransactionItems.price.label("item_amount"),
                Transactions.category.label("associated_category"),
                Transactions.created_at.label("date")
            )
            .join(Transactions, TransactionItems.transaction_id == Transactions.id)
            .where(
                Transactions.user_id == user_id,
                Transactions.type == "expense",
                Transactions.created_at >= start_date,
                Transactions.created_at < end_date
            )
            .order_by(desc(TransactionItems.price))
            .limit(30)
        )

    else:
        items_stmt = (
            select(
                TransactionItems.name,
                TransactionItems.price.label("item_amount"),
                Transactions.category.label("associated_category"),
                Transactions.created_at.label("date")
            )
            .join(Transactions, TransactionItems.transaction_id == Transactions.id)
            .where(
                Transactions.user_id == user_id,
                Transactions.type == "expense",
                Transactions.created_at >= start_date,
                Transactions.created_at < end_date
            )
            .order_by(Transactions.created_at.desc())

        )


    items_res = await session.execute(items_stmt)
    top_items = [
        {
            "name": r.name,
            "total_amount": float(r.item_amount),
            "category": r.associated_category,
            "date": r.date.strftime("%Y-%m-%d")
        }
        for r in items_res.all()
    ]


    net_balance = db_total_income - db_total_amount


    user_config = {
        "currency": user_bot.currency,
        "monthly_budget": float(user_bot.monthly_budget) if user_bot.monthly_budget else None,
        "budget_remind_percent": user_bot.budget_remind_percent,
        "savings_goal": float(user_bot.savings_goal) if user_bot.savings_goal else None,
    }


    return {
        "total_amount": round(db_total_amount, 2),
        "total_count": db_total_count,# maybe delete
        "total_income": round(db_total_income, 2),
        "net_balance": round(net_balance, 2),
        "categories": categories,
        "top_items": top_items,
        "days_period": actual_days,
        "user_config": user_config
    }