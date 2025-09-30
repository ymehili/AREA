"""Create area_steps table"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202509301200"
down_revision = "830e69042411"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "area_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("area_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_type", sa.String(length=50), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default='0'),
        sa.Column("service", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=255), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
            ["area_id"],
            ["areas.id"],
            name="fk_area_steps_area_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("area_id", "order", name="uq_area_steps_area_id_order"),
    )
    op.create_index("ix_area_steps_area_id", "area_steps", ["area_id"])
    op.create_index("ix_area_steps_area_id_order", "area_steps", ["area_id", "order"])


def downgrade() -> None:
    op.drop_index("ix_area_steps_area_id_order", table_name="area_steps")
    op.drop_index("ix_area_steps_area_id", table_name="area_steps")
    op.drop_table("area_steps")
