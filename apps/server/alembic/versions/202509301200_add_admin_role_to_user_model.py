"""Add admin role to user model

Revision ID: 202509301200
Revises: 830e69042411
Create Date: 2025-09-30 12:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202509301200"
down_revision = "830e69042411"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            default=False,
            server_default=sa.text("false")
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_admin")