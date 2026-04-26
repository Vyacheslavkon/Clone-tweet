from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class UserBot(Base):

    __tablename__ = "users_bot"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    first_name: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    language_code: Mapped[str] = mapped_column(String(10))
    subscription_type: Mapped[str] = mapped_column(default="free")  # free, pro
    sub_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    currency: Mapped[str] = mapped_column(default="RUB")
    monthly_budget: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=12, scale=2), nullable=True
    )  # limit expense
    budget_remind_percent: Mapped[int] = mapped_column(
        SmallInteger, default=80, server_default="80"
    )  # limit expense %

    savings_goal: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=12,
            scale=2,
        ),
        nullable=True,
    )  # amount of savings

    last_payment_id: Mapped[str | None] = mapped_column(String, nullable=True)

    ocr_requests_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )  # count checks

    ai_requests_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )

    last_request_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Transactions(Base):

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users_bot.id", ondelete="CASCADE"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    type: Mapped[str] = mapped_column(String(10))  # income, expense
    category: Mapped[str] = mapped_column(String(50), index=True)
    description: Mapped[str | None] = mapped_column(String(255))
    receipt_photo_url: Mapped[str | None] = mapped_column(Text)
    text_check: Mapped[str | None] = mapped_column(Text)
