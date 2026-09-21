# mypy: ignore-errors
#flake8: noqa
# type: ignore
"""add check constraints for positive amount and price

Revision ID: f275168c575d
Revises: 4c9bee231689
Create Date: 2026-09-21 11:51:35.776191

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f275168c575d'
down_revision: Union[str, Sequence[str], None] = '4c9bee231689'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        "ck_transactions_amount_positive",
        "transactions",
        "amount > 0",
    )
    op.create_check_constraint(
        "ck_transaction_items_price_positive",
        "transaction_items",
        "price >= 0",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_transaction_items_price_positive", "transaction_items", type_="check")
    op.drop_constraint("ck_transactions_amount_positive", "transactions", type_="check")