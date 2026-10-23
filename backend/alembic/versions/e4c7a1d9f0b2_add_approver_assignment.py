"""add an optional assigned human approver to requests

Revision ID: e4c7a1d9f0b2
Revises: d4e6f9a2b1c7
Create Date: 2026-10-22

This additive nullable column preserves existing requests. Existing rows can
continue to be assigned by an administrator after deployment.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4c7a1d9f0b2"
down_revision: Union[str, None] = "d4e6f9a2b1c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("requests", schema=None) as batch_op:
        batch_op.add_column(sa.Column("assigned_approver_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_requests_assigned_approver_id_users",
            "users",
            ["assigned_approver_id"],
            ["id"],
        )
        batch_op.create_index("ix_requests_assigned_approver_id", ["assigned_approver_id"])


def downgrade() -> None:
    with op.batch_alter_table("requests", schema=None) as batch_op:
        batch_op.drop_index("ix_requests_assigned_approver_id")
        batch_op.drop_constraint("fk_requests_assigned_approver_id_users", type_="foreignkey")
        batch_op.drop_column("assigned_approver_id")
