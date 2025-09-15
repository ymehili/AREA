"""Create users table"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202402041200"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("google_oauth_sub", sa.String(length=255), nullable=True),
        sa.Column("github_oauth_id", sa.String(length=255), nullable=True),
        sa.Column("microsoft_oauth_id", sa.String(length=255), nullable=True),
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
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("google_oauth_sub", name="uq_users_google_oauth_sub"),
        sa.UniqueConstraint("github_oauth_id", name="uq_users_github_oauth_id"),
        sa.UniqueConstraint(
            "microsoft_oauth_id",
            name="uq_users_microsoft_oauth_id",
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
