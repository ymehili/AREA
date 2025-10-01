"""Add is_suspended field to users table

Revision ID: a1b2c3d4e5f6
Revises: 830e69042411
Create Date: 2025-10-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import expression


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '830e69042411'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add the 'is_suspended' column to the 'users' table
    op.add_column('users', sa.Column('is_suspended', sa.Boolean(), 
                                     server_default=expression.false(), 
                                     nullable=False))


def downgrade() -> None:
    # Drop the 'is_suspended' column from the 'users' table
    op.drop_column('users', 'is_suspended')