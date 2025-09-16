"""Utilities for running Alembic migrations from application code."""

from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

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
    return alembic_cfg


def run_migrations() -> None:
    """Apply all pending migrations up to the latest revision."""

    logger.info("Applying database migrations (alembic upgrade head)")
    command.upgrade(_alembic_config(), "head")


__all__ = ["run_migrations"]

