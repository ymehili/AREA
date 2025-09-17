"""Create areas table"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202509171932"
down_revision = "202503010002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "areas",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("trigger_service", sa.String(length=255), nullable=False),
        sa.Column("trigger_action", sa.String(length=255), nullable=False),
        sa.Column("reaction_service", sa.String(length=255), nullable=False),
        sa.Column("reaction_action", sa.String(length=255), nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            default=True,
            server_default='true',
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
    )
    op.create_index(
        "ix_areas_user_id", "areas", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_areas_user_id", table_name="areas")
    op.drop_table("areas")