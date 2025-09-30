"""Area steps refactor - introduce multi-step workflows

Revision ID: 202509301200
Revises: 202509291800
Create Date: 2025-09-30 12:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text
import uuid as uuid_module

# revision identifiers, used by Alembic.
revision = "202509301200"
down_revision = "202509291800"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Introduce area_steps table and migrate existing trigger/reaction pairs."""

    # Create the step_type enum
    op.execute(text(
        "CREATE TYPE areasteptype AS ENUM ('action', 'reaction', 'condition', 'delay')"
    ))

    # Create area_steps table
    op.create_table(
        "area_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4),
        sa.Column("area_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("areas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("step_type", sa.Enum("action", "reaction", "condition", "delay", name="areasteptype", native_enum=False), nullable=False),
        sa.Column("service_slug", sa.String(length=255), nullable=True),
        sa.Column("action_key", sa.String(length=255), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("area_id", "position", name="uq_area_steps_area_id_position"),
    )

    # Create indexes
    op.create_index("ix_area_steps_area_id", "area_steps", ["area_id"])
    op.create_index("ix_area_steps_step_type", "area_steps", ["step_type"])

    # Data migration: Convert existing areas to step format
    connection = op.get_bind()

    # Fetch all existing areas
    areas_result = connection.execute(text(
        """
        SELECT id, trigger_service, trigger_action, trigger_params,
               reaction_service, reaction_action, reaction_params
        FROM areas
        """
    ))

    areas = areas_result.fetchall()

    # Insert two steps for each area
    for area in areas:
        area_id = area[0]

        # Insert ACTION step (position 0) from trigger fields
        connection.execute(text(
            """
            INSERT INTO area_steps (id, area_id, position, step_type, service_slug, action_key, config, created_at, updated_at)
            VALUES (:id, :area_id, 0, 'action', :service_slug, :action_key, :config, NOW(), NOW())
            """
        ), {
            "id": str(uuid_module.uuid4()),
            "area_id": str(area_id),
            "service_slug": area[1],  # trigger_service
            "action_key": area[2],     # trigger_action
            "config": area[3],         # trigger_params (already JSON)
        })

        # Insert REACTION step (position 1) from reaction fields
        connection.execute(text(
            """
            INSERT INTO area_steps (id, area_id, position, step_type, service_slug, action_key, config, created_at, updated_at)
            VALUES (:id, :area_id, 1, 'reaction', :service_slug, :action_key, :config, NOW(), NOW())
            """
        ), {
            "id": str(uuid_module.uuid4()),
            "area_id": str(area_id),
            "service_slug": area[4],  # reaction_service
            "action_key": area[5],     # reaction_action
            "config": area[6],         # reaction_params (already JSON)
        })

        # Update area's updated_at timestamp
        connection.execute(text(
            "UPDATE areas SET updated_at = NOW() WHERE id = :area_id"
        ), {"area_id": str(area_id)})

    # Drop legacy columns from areas table
    op.drop_column("areas", "reaction_params")
    op.drop_column("areas", "reaction_action")
    op.drop_column("areas", "reaction_service")
    op.drop_column("areas", "trigger_params")
    op.drop_column("areas", "trigger_action")
    op.drop_column("areas", "trigger_service")


def downgrade() -> None:
    """Restore single trigger/reaction schema and migrate step data back."""

    # Recreate the legacy columns
    op.add_column("areas", sa.Column("trigger_service", sa.String(length=255), nullable=True))
    op.add_column("areas", sa.Column("trigger_action", sa.String(length=255), nullable=True))
    op.add_column("areas", sa.Column("trigger_params", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("areas", sa.Column("reaction_service", sa.String(length=255), nullable=True))
    op.add_column("areas", sa.Column("reaction_action", sa.String(length=255), nullable=True))
    op.add_column("areas", sa.Column("reaction_params", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # Data migration: Repopulate legacy columns from steps
    connection = op.get_bind()

    # Fetch all areas
    areas_result = connection.execute(text("SELECT id FROM areas"))
    areas = areas_result.fetchall()

    for area in areas:
        area_id = area[0]

        # Get first ACTION step
        action_step = connection.execute(text(
            """
            SELECT service_slug, action_key, config
            FROM area_steps
            WHERE area_id = :area_id AND step_type = 'action'
            ORDER BY position ASC
            LIMIT 1
            """
        ), {"area_id": str(area_id)}).fetchone()

        # Get first REACTION step
        reaction_step = connection.execute(text(
            """
            SELECT service_slug, action_key, config
            FROM area_steps
            WHERE area_id = :area_id AND step_type = 'reaction'
            ORDER BY position ASC
            LIMIT 1
            """
        ), {"area_id": str(area_id)}).fetchone()

        # Update area with legacy fields
        if action_step and reaction_step:
            connection.execute(text(
                """
                UPDATE areas
                SET trigger_service = :trigger_service,
                    trigger_action = :trigger_action,
                    trigger_params = :trigger_params,
                    reaction_service = :reaction_service,
                    reaction_action = :reaction_action,
                    reaction_params = :reaction_params,
                    updated_at = NOW()
                WHERE id = :area_id
                """
            ), {
                "area_id": str(area_id),
                "trigger_service": action_step[0],
                "trigger_action": action_step[1],
                "trigger_params": action_step[2],
                "reaction_service": reaction_step[0],
                "reaction_action": reaction_step[1],
                "reaction_params": reaction_step[2],
            })

    # Make legacy columns non-nullable after populating them
    op.alter_column("areas", "trigger_service", nullable=False)
    op.alter_column("areas", "trigger_action", nullable=False)
    op.alter_column("areas", "reaction_service", nullable=False)
    op.alter_column("areas", "reaction_action", nullable=False)

    # Drop area_steps table and indexes
    op.drop_index("ix_area_steps_step_type", "area_steps")
    op.drop_index("ix_area_steps_area_id", "area_steps")
    op.drop_table("area_steps")

    # Drop the enum type
    op.execute(text("DROP TYPE areasteptype"))
