"""add structured expense claim fields

Revision ID: d4e6f9a2b1c7
Revises: b2f4a1c9d0e3
Create Date: 2026-10-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e6f9a2b1c7"
down_revision: Union[str, None] = "b2f4a1c9d0e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("requests", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("expense_category", sa.String(length=80), nullable=False, server_default="other")
        )
        batch_op.add_column(sa.Column("claimed_amount", sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column("expense_date", sa.Date(), nullable=True))
        batch_op.add_column(
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR")
        )


def downgrade() -> None:
    with op.batch_alter_table("requests", schema=None) as batch_op:
        batch_op.drop_column("currency")
        batch_op.drop_column("expense_date")
        batch_op.drop_column("claimed_amount")
        batch_op.drop_column("expense_category")
