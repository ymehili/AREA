"""Create admin audit logs table

Revision ID: 202510011200
Revises: a1b2c3d4e5f6
Create Date: 2025-10-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '202510011200'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create admin_audit_logs table
    op.create_table(
        'admin_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('admin_user_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_user_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('details', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better query performance
    op.create_index(op.f('ix_admin_audit_logs_admin_user_id'), 'admin_audit_logs', 
                    ['admin_user_id'])
    op.create_index(op.f('ix_admin_audit_logs_target_user_id'), 'admin_audit_logs', 
                    ['target_user_id'])
    op.create_index(op.f('ix_admin_audit_logs_action_type'), 'admin_audit_logs', 
                    ['action_type'])
    op.create_index(op.f('ix_admin_audit_logs_created_at'), 'admin_audit_logs', 
                    ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_admin_audit_logs_created_at'), table_name='admin_audit_logs')
    op.drop_index(op.f('ix_admin_audit_logs_action_type'), table_name='admin_audit_logs')
    op.drop_index(op.f('ix_admin_audit_logs_target_user_id'), table_name='admin_audit_logs')
    op.drop_index(op.f('ix_admin_audit_logs_admin_user_id'), table_name='admin_audit_logs')
    
    # Drop admin_audit_logs table
    op.drop_table('admin_audit_logs')