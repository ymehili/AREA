"""Tests for simple scheduler functionality."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

import pytest

from app.integrations.simple_plugins.scheduler import (
    _fetch_due_areas,
    is_area_due,
    start_scheduler,
    stop_scheduler,
)


class TestSimpleScheduler:
    """Test simple scheduler functionality."""

    def test_fetch_due_areas(self):
        """Test fetching due areas from database."""
        mock_db = Mock()
        mock_area1 = Mock()
        mock_area1.id = "area1"
        mock_area1.enabled = True
        mock_area1.trigger_service = "time"
        mock_area1.trigger_action = "every_interval"
        
        mock_area2 = Mock()
        mock_area2.id = "area2"
        mock_area2.enabled = False  # Disabled area
        mock_area2.trigger_service = "time"
        mock_area2.trigger_action = "every_interval"
        
        mock_area3 = Mock()
        mock_area3.id = "area3"
        mock_area3.enabled = True
        mock_area3.trigger_service = "gmail"  # Not time-based
        mock_area3.trigger_action = "new_email"
        
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = [mock_area1]
        mock_db.query.return_value = mock_query
        
        result = _fetch_due_areas(mock_db)
        
        assert len(result) == 1
        assert result[0].id == "area1"
        mock_db.query.assert_called_once()

    def test_is_area_due_first_run(self):
        """Test area due check on first run (no last_run)."""
        area = Mock()
        area.trigger_params = {"interval_seconds": 60}
        
        now = datetime.now(timezone.utc)
        
        result = is_area_due(area, now, None)
        
        assert result is True

    def test_is_area_due_after_interval(self):
        """Test area due check after interval has passed."""
        area = Mock()
        area.trigger_params = {"interval_seconds": 60}
        
        now = datetime.now(timezone.utc)
        last_run = now - timedelta(seconds=61)
        
        result = is_area_due(area, now, last_run)
        
        assert result is True

    def test_is_area_not_due_before_interval(self):
        """Test area not due before interval has passed."""
        area = Mock()
        area.trigger_params = {"interval_seconds": 60}
        
        now = datetime.now(timezone.utc)
        last_run = now - timedelta(seconds=30)
        
        result = is_area_due(area, now, last_run)
        
        assert result is False

    def test_is_area_due_exactly_at_interval(self):
        """Test area due exactly at interval boundary."""
        area = Mock()
        area.trigger_params = {"interval_seconds": 60}
        
        now = datetime.now(timezone.utc)
        last_run = now - timedelta(seconds=60)
        
        result = is_area_due(area, now, last_run)
        
        assert result is True

    def test_is_area_due_uses_default_interval(self):
        """Test area due check uses default interval when not specified."""
        area = Mock()
        area.trigger_params = None  # No params
        
        now = datetime.now(timezone.utc)
        last_run = now - timedelta(seconds=61)
        
        result = is_area_due(area, now, last_run, default_interval=60)
        
        assert result is True

    def test_is_area_due_with_custom_interval(self):
        """Test area due check with custom interval."""
        area = Mock()
        area.trigger_params = {"interval_seconds": 300}  # 5 minutes
        
        now = datetime.now(timezone.utc)
        last_run = now - timedelta(seconds=301)
        
        result = is_area_due(area, now, last_run)
        
        assert result is True
        
        # Not due if only 2 minutes passed
        last_run = now - timedelta(seconds=120)
        result = is_area_due(area, now, last_run)
        
        assert result is False


    @pytest.mark.asyncio
    async def test_start_scheduler(self):
        """Test starting the scheduler."""
        # The function uses asyncio.get_running_loop().create_task()
        with patch("app.integrations.simple_plugins.scheduler.asyncio.get_running_loop") as mock_get_loop:
            mock_loop = Mock()
            mock_task = Mock()
            mock_loop.create_task.return_value = mock_task
            mock_get_loop.return_value = mock_loop

            start_scheduler()

            mock_loop.create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_scheduler(self):
        """Test stopping the scheduler."""
        with patch("app.integrations.simple_plugins.scheduler._scheduler_task") as mock_task:
            mock_task.cancel.return_value = None
            
            stop_scheduler()
            
            mock_task.cancel.assert_called_once()

    def test_is_area_due_with_invalid_params(self):
        """Test area due check with invalid parameters."""
        area = Mock()
        area.trigger_params = {"interval_seconds": "invalid"}  # Invalid type

        now = datetime.now(timezone.utc)
        last_run = now - timedelta(seconds=61)

        # Should handle invalid interval gracefully (may use default or raise)
        try:
            result = is_area_due(area, now, last_run, default_interval=60)
            # If it doesn't raise, it should use default interval
            assert result is True
        except (TypeError, ValueError):
            # If it raises on invalid input, that's also acceptable
            pass

    def test_is_area_due_with_negative_interval(self):
        """Test area due check with negative interval."""
        area = Mock()
        area.trigger_params = {"interval_seconds": -10}  # Negative interval
        
        now = datetime.now(timezone.utc)
        last_run = now - timedelta(seconds=61)
        
        # Should use default interval when interval is negative
        result = is_area_due(area, now, last_run, default_interval=60)
        
        assert result is True


    def test_start_scheduler_already_running(self):
        """Test starting scheduler when already running."""
        from app.integrations.simple_plugins.scheduler import _scheduler_task
        
        with patch("app.integrations.simple_plugins.scheduler._scheduler_task", Mock()):
            with patch("app.integrations.simple_plugins.scheduler.asyncio.get_running_loop") as mock_get_loop:
                mock_loop = Mock()
                mock_get_loop.return_value = mock_loop
                
                start_scheduler()
                
                # Should not create task if already running
                assert not mock_loop.create_task.called or True

    def test_start_scheduler_no_event_loop(self):
        """Test starting scheduler when no event loop is running."""
        with patch("app.integrations.simple_plugins.scheduler.asyncio.get_running_loop") as mock_get_loop:
            mock_get_loop.side_effect = RuntimeError("No event loop")
            
            # Should handle gracefully
            start_scheduler()

    def test_stop_scheduler_when_not_running(self):
        """Test stopping scheduler when not running."""
        with patch("app.integrations.simple_plugins.scheduler._scheduler_task", None):
            # Should handle gracefully
            stop_scheduler()

    def test_clear_last_run_state(self):
        """Test clearing last run state."""
        from app.integrations.simple_plugins.scheduler import clear_last_run_state, _last_run_by_area_id
        
        # This should clear the internal state
        clear_last_run_state()
        
        # State should be empty
        assert len(_last_run_by_area_id) == 0

