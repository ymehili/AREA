"""Add OAuth metadata to service connections."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202412211500"
# This migration only depends on the service_connections table existing,
# which was created in revision 202402051200. Point to that to avoid
# creating an unnecessary branch head.
down_revision = "202402051200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add OAuth metadata column to service_connections table."""
    # Add metadata column for storing provider-specific data
    op.add_column(
        "service_connections",
        sa.Column(
            "oauth_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Provider-specific OAuth metadata",
        ),
    )

    # Add index for better query performance
    op.create_index(
        "ix_service_connections_oauth_metadata",
        "service_connections",
        ["oauth_metadata"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Remove OAuth metadata column from service_connections table."""
    op.drop_index("ix_service_connections_oauth_metadata", table_name="service_connections")
    op.drop_column("service_connections", "oauth_metadata")