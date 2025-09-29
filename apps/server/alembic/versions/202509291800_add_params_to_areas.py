"""Add trigger_params and reaction_params to areas"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202509291800"
down_revision = "202509171932"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "areas",
        sa.Column("trigger_params", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "areas",
        sa.Column("reaction_params", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("areas", "reaction_params")
    op.drop_column("areas", "trigger_params")