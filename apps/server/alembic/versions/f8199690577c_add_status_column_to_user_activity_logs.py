"""Add status column to user_activity_logs table

Revision ID: f8199690577c
Revises: 9b5f6b9b7c4d
Create Date: 2025-10-07 19:45:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'f8199690577c'
down_revision = '9b5f6b9b7c4d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add status column to user_activity_logs table with default value
    op.add_column('user_activity_logs', sa.Column('status', sa.String(length=20), nullable=False, server_default='success'))
    
    # Create index for the status column
    op.create_index('ix_user_activity_logs_status', 'user_activity_logs', ['status'])


def downgrade() -> None:
    # Drop index for the status column
    op.drop_index('ix_user_activity_logs_status', table_name='user_activity_logs')
    
    # Drop status column from user_activity_logs table
    op.drop_column('user_activity_logs', 'status')