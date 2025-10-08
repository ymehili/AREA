"""Unit tests for simple plugins (time triggers and debug reactions)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from app.integrations.simple_plugins.registry import PluginsRegistry
from app.integrations.simple_plugins.scheduler import is_area_due
from app.models.area import Area


class TestPluginsRegistry:
    """Test the plugins registry."""

    def test_registry_initialization(self):
        """Test that registry initializes with default handlers."""
        registry = PluginsRegistry()
        handler = registry.get_reaction_handler("debug", "log")
        assert handler is not None

    def test_get_nonexistent_handler(self):
        """Test getting a handler that doesn't exist."""
        registry = PluginsRegistry()
        handler = registry.get_reaction_handler("nonexistent", "action")
        assert handler is None

    def test_debug_log_handler_basic(self, caplog):
        """Test debug log handler with basic message."""
        import logging
        caplog.set_level(logging.INFO, logger="area")

        registry = PluginsRegistry()
        handler = registry.get_reaction_handler("debug", "log")

        # Create mock area
        area = Mock(spec=Area)
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"
        area.trigger_service = "time"
        area.trigger_action = "every_interval"
        area.reaction_service = "debug"
        area.reaction_action = "log"

        # Create event
        now_str = "2025-09-29T12:00:00Z"
        event = {
            "now": now_str,
            "area_id": "test-area-id",
            "user_id": "test-user-id",
            "tick": True,
        }

        # Execute handler
        params = {"message": "Test message at {{ now }}"}
        handler(area, params, event)

        # Verify log was created
        area_logs = [r for r in caplog.records if r.name == "area"]
        assert len(area_logs) > 0, f"Expected logs from 'area' logger, got {len(caplog.records)} total records: {[r.name for r in caplog.records]}"
        assert "area_run" in area_logs[0].message
        # The message should contain the resolved variable
        assert "Test message at 2025-09-29T12:00:00Z" in area_logs[0].message

    def test_debug_log_handler_with_area_name(self, caplog):
        """Test debug log handler with area name template."""
        import logging
        caplog.set_level(logging.INFO, logger="area")

        registry = PluginsRegistry()
        handler = registry.get_reaction_handler("debug", "log")

        area = Mock(spec=Area)
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "My Test Area"
        area.trigger_service = "time"
        area.trigger_action = "every_interval"
        area.reaction_service = "debug"
        area.reaction_action = "log"

        event = {
            "now": "2025-09-29T12:00:00Z",
            "area_id": "test-area-id",
            "user_id": "test-user-id",
            "tick": True,
        }

        params = {"message": "Ping from {{ area.name }} at {{ now }}"}
        handler(area, params, event)

        area_logs = [r for r in caplog.records if r.name == "area"]
        assert len(area_logs) > 0
        assert "Ping from My Test Area at 2025-09-29T12:00:00Z" in area_logs[0].message

    def test_debug_log_handler_default_message(self, caplog):
        """Test debug log handler with default message when no message provided."""
        import logging
        caplog.set_level(logging.INFO, logger="area")

        registry = PluginsRegistry()
        handler = registry.get_reaction_handler("debug", "log")

        area = Mock(spec=Area)
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"
        area.trigger_service = "time"
        area.trigger_action = "every_interval"
        area.reaction_service = "debug"
        area.reaction_action = "log"

        event = {
            "now": "2025-09-29T12:00:00Z",
            "area_id": "test-area-id",
            "user_id": "test-user-id",
            "tick": True,
        }

        # No message in params
        params = {}
        handler(area, params, event)

        area_logs = [r for r in caplog.records if r.name == "area"]
        assert len(area_logs) > 0
        assert "Area triggered at 2025-09-29T12:00:00Z" in area_logs[0].message


class TestSchedulerLogic:
    """Test scheduler due logic."""

    def test_area_due_first_run(self):
        """Test that area is due on first run (no last_run)."""
        area = Mock(spec=Area)
        area.trigger_params = {"interval_seconds": 60}

        now = datetime.now(timezone.utc)
        assert is_area_due(area, now, None) is True

    def test_area_due_after_interval(self):
        """Test that area is due after interval has passed."""
        area = Mock(spec=Area)
        area.trigger_params = {"interval_seconds": 60}

        now = datetime.now(timezone.utc)
        last_run = now - timedelta(seconds=61)

        assert is_area_due(area, now, last_run) is True

    def test_area_not_due_before_interval(self):
        """Test that area is not due before interval has passed."""
        area = Mock(spec=Area)
        area.trigger_params = {"interval_seconds": 60}

        now = datetime.now(timezone.utc)
        last_run = now - timedelta(seconds=30)

        assert is_area_due(area, now, last_run) is False

    def test_area_due_exactly_at_interval(self):
        """Test that area is due exactly at interval boundary."""
        area = Mock(spec=Area)
        area.trigger_params = {"interval_seconds": 60}

        now = datetime.now(timezone.utc)
        last_run = now - timedelta(seconds=60)

        assert is_area_due(area, now, last_run) is True

    def test_area_due_uses_default_interval(self):
        """Test that default interval is used when not specified."""
        area = Mock(spec=Area)
        area.trigger_params = None  # No params

        now = datetime.now(timezone.utc)
        last_run = now - timedelta(seconds=61)

        # Should use default of 60 seconds
        assert is_area_due(area, now, last_run, default_interval=60) is True

    def test_area_due_with_custom_interval(self):
        """Test with a custom interval."""
        area = Mock(spec=Area)
        area.trigger_params = {"interval_seconds": 300}  # 5 minutes

        now = datetime.now(timezone.utc)
        last_run = now - timedelta(seconds=301)

        assert is_area_due(area, now, last_run) is True

        # Not due if only 2 minutes passed
        last_run = now - timedelta(seconds=120)
        assert is_area_due(area, now, last_run) is False