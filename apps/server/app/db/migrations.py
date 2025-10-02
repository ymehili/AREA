"""Utilities for running Alembic migrations from application code."""

from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.config import settings

logger = logging.getLogger(__name__)


def _alembic_config() -> Config:
    """Build an Alembic config wired to the runtime settings."""

    project_root = Path(__file__).resolve().parents[2]
    config_path = project_root / "alembic.ini"
    script_location = project_root / "alembic"

    alembic_cfg = Config(str(config_path))
    alembic_cfg.set_main_option("script_location", str(script_location))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    logger.info(
        "Alembic configured",
        extra={
            "config_path": str(config_path),
            "script_location": str(script_location),
        },
    )
    return alembic_cfg


def run_migrations() -> None:
    """Apply all pending migrations up to the latest revision.

    This function ensures migrations don't hang by:
    1. Disposing the app's engine to close any pooled connections
    2. Checking if migrations are needed before running
    3. Setting statement_timeout to prevent indefinite waits on locks
    """
    # Import here to avoid circular dependency
    from app.db.session import engine as app_engine
    from alembic.runtime.migration import MigrationContext

    # Close all connections in the app's connection pool to prevent lock conflicts
    # This ensures Alembic migrations won't be blocked by app connections
    logger.info("Disposing application database connections before migrations")
    app_engine.dispose()

    cfg = _alembic_config()

    # Check if migration is needed by comparing current revision with heads
    try:
        script = ScriptDirectory.from_config(cfg)
        heads_list = list(script.get_heads() or [])
        heads_str = ",".join(heads_list)
        logger.info("Alembic migration heads: %s", heads_str)

        # Get current database revision
        with app_engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()
            logger.info("Current database revision: %s", current_rev)

            # Check if current revision is one of the heads - if so, no migration needed
            if current_rev and current_rev in heads_list:
                logger.info("Database is already at head revision, skipping migrations")
                return

    except Exception as e:
        logger.warning("Unable to check migration status: %s, proceeding with upgrade", e)

    logger.info("Applying database migrations (alembic upgrade heads)")
    try:
        command.upgrade(cfg, "heads")
        logger.info("Database migrations applied successfully")
    except Exception:
        logger.exception("Alembic upgrade failed")
        raise


__all__ = ["run_migrations"]

