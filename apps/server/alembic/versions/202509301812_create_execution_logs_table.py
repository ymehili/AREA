"""Create execution_logs table"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202509301812"
down_revision = "202509171932"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "execution_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("area_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("output", sa.String(length=5000), nullable=True),
        sa.Column("error_message", sa.String(length=5000), nullable=True),
        sa.Column("step_details", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["area_id"],
            ["areas.id"],
        ),
    )
    op.create_index(
        "ix_execution_logs_area_id", "execution_logs", ["area_id"]
    )
    op.create_index(
        "ix_execution_logs_timestamp", "execution_logs", ["timestamp"]
    )
    op.create_index(
        "ix_execution_logs_status", "execution_logs", ["status"]
    )


def downgrade() -> None:
    op.drop_index("ix_execution_logs_area_id", table_name="execution_logs")
    op.drop_index("ix_execution_logs_timestamp", table_name="execution_logs")
    op.drop_index("ix_execution_logs_status", table_name="execution_logs")
    op.drop_table("execution_logs")