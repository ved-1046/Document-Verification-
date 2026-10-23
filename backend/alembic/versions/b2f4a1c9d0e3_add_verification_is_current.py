"""add verification is_current

Revision ID: b2f4a1c9d0e3
Revises: caecba7fc513
Create Date: 2026-10-20 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2f4a1c9d0e3"
down_revision: Union[str, None] = "caecba7fc513"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("verification_checks", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_current", sa.Boolean(), server_default="1", nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("verification_checks", schema=None) as batch_op:
        batch_op.drop_column("is_current")
