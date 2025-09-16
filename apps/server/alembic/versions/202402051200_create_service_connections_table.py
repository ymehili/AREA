"""Create service_connections table"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202402051200"
down_revision = "202402041200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_name", sa.String(length=255), nullable=False),
        sa.Column("encrypted_access_token", sa.String(length=1024), nullable=False),
        sa.Column("encrypted_refresh_token", sa.String(length=1024), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint(
            "user_id", "service_name", name="uq_service_connections_user_id_service_name"
        ),
    )
    op.create_index(
        "ix_service_connections_user_id", "service_connections", ["user_id"]
    )
    op.create_index(
        "ix_service_connections_service_name", "service_connections", ["service_name"]
    )


def downgrade() -> None:
    op.drop_index("ix_service_connections_service_name", table_name="service_connections")
    op.drop_index("ix_service_connections_user_id", table_name="service_connections")
    op.drop_table("service_connections")