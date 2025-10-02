"""Tests for database migrations utilities."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from alembic.config import Config

from app.db.migrations import run_migrations


def test_run_migrations_success() -> None:
    """Test successful migration execution."""
    with patch("app.db.migrations._alembic_config") as mock_config:
        with patch("app.db.migrations.command") as mock_command:
            with patch("app.db.migrations.ScriptDirectory") as mock_script_dir:
                with patch("app.db.session.engine") as mock_engine:
                    # Setup mock config
                    mock_cfg = MagicMock(spec=Config)
                    mock_config.return_value = mock_cfg

                    # Setup mock script directory
                    mock_script = MagicMock()
                    mock_script.get_heads.return_value = ["abc123", "def456"]
                    mock_script_dir.from_config.return_value = mock_script

                    # Setup mock connection to return current revision different from heads
                    mock_connection = MagicMock()
                    mock_context = MagicMock()
                    mock_context.get_current_revision.return_value = "old123"  # Different from heads
                    mock_connection.__enter__ = MagicMock(return_value=mock_connection)
                    mock_connection.__exit__ = MagicMock(return_value=None)
                    mock_engine.connect.return_value = mock_connection

                    with patch("alembic.runtime.migration.MigrationContext") as mock_migration_context:
                        mock_migration_context.configure.return_value = mock_context

                        # Run migrations
                        run_migrations()

                        # Verify upgrade command was called
                        mock_command.upgrade.assert_called_once_with(mock_cfg, "heads")


def test_run_migrations_upgrade_fails() -> None:
    """Test migration failure handling."""
    with patch("app.db.migrations._alembic_config") as mock_config:
        with patch("app.db.migrations.command") as mock_command:
            with patch("app.db.migrations.ScriptDirectory") as mock_script_dir:
                with patch("app.db.session.engine") as mock_engine:
                    # Setup mock config
                    mock_cfg = MagicMock(spec=Config)
                    mock_config.return_value = mock_cfg

                    # Setup mock script directory
                    mock_script = MagicMock()
                    mock_script.get_heads.return_value = ["abc123"]
                    mock_script_dir.from_config.return_value = mock_script

                    # Setup mock connection to return current revision different from head
                    mock_connection = MagicMock()
                    mock_context = MagicMock()
                    mock_context.get_current_revision.return_value = "old123"  # Different from head
                    mock_connection.__enter__ = MagicMock(return_value=mock_connection)
                    mock_connection.__exit__ = MagicMock(return_value=None)
                    mock_engine.connect.return_value = mock_connection

                    with patch("alembic.runtime.migration.MigrationContext") as mock_migration_context:
                        mock_migration_context.configure.return_value = mock_context

                        # Make upgrade fail
                        mock_command.upgrade.side_effect = Exception("Migration failed")

                        # Verify exception is raised
                        with pytest.raises(Exception, match="Migration failed"):
                            run_migrations()


def test_run_migrations_already_at_head() -> None:
    """Test that migrations are skipped when database is already at head."""
    with patch("app.db.migrations._alembic_config") as mock_config:
        with patch("app.db.migrations.command") as mock_command:
            with patch("app.db.migrations.ScriptDirectory") as mock_script_dir:
                with patch("app.db.session.engine") as mock_engine:
                    # Setup mock config
                    mock_cfg = MagicMock(spec=Config)
                    mock_config.return_value = mock_cfg

                    # Setup mock script directory
                    mock_script = MagicMock()
                    mock_script.get_heads.return_value = ["abc123"]
                    mock_script_dir.from_config.return_value = mock_script

                    # Setup mock connection to return current revision same as head
                    mock_connection = MagicMock()
                    mock_context = MagicMock()
                    mock_context.get_current_revision.return_value = "abc123"  # Same as head
                    mock_connection.__enter__ = MagicMock(return_value=mock_connection)
                    mock_connection.__exit__ = MagicMock(return_value=None)
                    mock_engine.connect.return_value = mock_connection

                    with patch("alembic.runtime.migration.MigrationContext") as mock_migration_context:
                        mock_migration_context.configure.return_value = mock_context

                        # Run migrations
                        run_migrations()

                        # Verify upgrade command was NOT called
                        mock_command.upgrade.assert_not_called()

