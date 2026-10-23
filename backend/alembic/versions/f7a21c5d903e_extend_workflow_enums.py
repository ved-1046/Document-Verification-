"""add admin role and reviewer completion / approval statuses

Revision ID: f7a21c5d903e
Revises: e4c7a1d9f0b2
Create Date: 2026-10-22

The application stores SQLAlchemy enums as strings in SQLite, so no table
rewrite is needed there. PostgreSQL uses native enums and needs additive
values before the new roles and transitions can be persisted.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "f7a21c5d903e"
down_revision: Union[str, None] = "e4c7a1d9f0b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    # PostgreSQL requires enum additions to commit before values can be used.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'admin'")
        op.execute("ALTER TYPE requeststatus ADD VALUE IF NOT EXISTS 'pending_approval'")
        op.execute("ALTER TYPE reviewactiontype ADD VALUE IF NOT EXISTS 'review_completed'")


def downgrade() -> None:
    # PostgreSQL cannot safely remove enum labels without rewriting every row.
    # Retain additive enum labels on downgrade; older app code ignores them.
    pass
