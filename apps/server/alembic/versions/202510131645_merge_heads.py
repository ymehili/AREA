"""Merge migration heads

Revision ID: 202510131645
Revises: 202510131640, f8199690577c
Create Date: 2025-10-13 16:45:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202510131645"
down_revision = ("202510131640", "f8199690577c")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge migration heads - no changes needed."""
    pass


def downgrade() -> None:
    """Downgrade merge - no changes needed."""
    pass
