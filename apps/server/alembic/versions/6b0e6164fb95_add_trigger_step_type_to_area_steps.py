"""Add trigger step type to area_steps

Revision ID: 6b0e6164fb95
Revises: 50edd2fa5c39
Create Date: 2025-10-01 15:59:07.981596

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b0e6164fb95'
down_revision: Union[str, None] = '50edd2fa5c39'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update the comment to reflect the new trigger type
    op.alter_column('area_steps', 'step_type',
               existing_type=sa.String(length=50),
               comment='Step type: trigger, action, reaction, condition, or delay',
               existing_nullable=False)
    
    # Add a check constraint to ensure valid step types
    op.execute("ALTER TABLE area_steps ADD CONSTRAINT chk_step_type CHECK (step_type IN ('trigger', 'action', 'reaction', 'condition', 'delay'))")


def downgrade() -> None:
    # Remove the check constraint
    op.execute("ALTER TABLE area_steps DROP CONSTRAINT chk_step_type")
    
    # Revert the comment to exclude 'trigger' (assuming previous comment didn't include it)
    op.alter_column('area_steps', 'step_type',
               existing_type=sa.String(length=50),
               comment='Step type: action, reaction, condition, or delay',
               existing_nullable=False)
