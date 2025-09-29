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
    """Apply all pending migrations up to the latest revision."""

    cfg = _alembic_config()
    # Log migration heads known to the script directory
    try:
        script = ScriptDirectory.from_config(cfg)
        heads = ",".join(script.get_heads() or [])
        logger.info("Alembic migration heads: %s", heads)
    except Exception as e:  # pragma: no cover - logging only
        logger.warning("Unable to read Alembic heads: %s", e)

    logger.info("Applying database migrations (alembic upgrade heads)")
    try:
        command.upgrade(cfg, "heads")
    except Exception:
        logger.exception("Alembic upgrade failed")
        raise
    logger.info("Database migrations applied successfully")


__all__ = ["run_migrations"]

