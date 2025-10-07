"""Add user_activity_logs table

Revision ID: 9b5f6b9b7c4d
Revises: fc5760e6871a
Create Date: 2025-10-07 15:32:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '9b5f6b9b7c4d'
down_revision = 'fc5760e6871a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_activity_logs table
    op.create_table(
        'user_activity_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('details', sa.String(length=5000), nullable=True),
        sa.Column('service_name', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_user_activity_logs_user_id', 'user_activity_logs', ['user_id'])
    op.create_index('ix_user_activity_logs_timestamp', 'user_activity_logs', ['timestamp'])
    op.create_index('ix_user_activity_logs_action_type', 'user_activity_logs', ['action_type'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_user_activity_logs_action_type', table_name='user_activity_logs')
    op.drop_index('ix_user_activity_logs_timestamp', table_name='user_activity_logs')
    op.drop_index('ix_user_activity_logs_user_id', table_name='user_activity_logs')

    # Drop user_activity_logs table
    op.drop_table('user_activity_logs')