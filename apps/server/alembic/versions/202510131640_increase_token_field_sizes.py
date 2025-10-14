"""Increase token field sizes for Microsoft tokens

Revision ID: 202510131640
Revises: fc5760e6871a
Create Date: 2025-10-13 16:40:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202510131640"
down_revision = "fc5760e6871a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Increase encrypted token field sizes from 1024 to 2048 characters.
    
    Microsoft Graph API tokens are longer than Google tokens and when encrypted
    can exceed the 1024 character limit.
    """
    op.alter_column(
        "service_connections",
        "encrypted_access_token",
        type_=sa.String(length=2048),
        existing_type=sa.String(length=1024),
        existing_nullable=False,
    )
    op.alter_column(
        "service_connections",
        "encrypted_refresh_token",
        type_=sa.String(length=2048),
        existing_type=sa.String(length=1024),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Revert token field sizes back to 1024 characters."""
    op.alter_column(
        "service_connections",
        "encrypted_access_token",
        type_=sa.String(length=1024),
        existing_type=sa.String(length=2048),
        existing_nullable=False,
    )
    op.alter_column(
        "service_connections",
        "encrypted_refresh_token",
        type_=sa.String(length=1024),
        existing_type=sa.String(length=2048),
        existing_nullable=True,
    )
