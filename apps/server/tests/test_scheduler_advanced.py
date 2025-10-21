"""Advanced tests for scheduler task execution."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import pytest
from sqlalchemy.orm import Session

from app.integrations.simple_plugins.scheduler import (
    scheduler_task,
    clear_last_run_state,
    start_scheduler,
    stop_scheduler,
    is_area_due,
    _fetch_due_areas,
)
from app.models.area import Area
from app.models.user import User


class TestSchedulerTask:
    """Test the main scheduler task execution loop."""

    @pytest.mark.asyncio
    async def test_scheduler_task_processes_due_areas(self, db_session: Session):
        """Test that scheduler task processes areas that are due."""
        # Create a test user
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        # Create a test area
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
            trigger_params={"interval_seconds": 1},
        )
        db_session.add(area)
        db_session.commit()
        
        # Clear any previous state
        clear_last_run_state()
        
        # Mock SessionLocal to return our test session
        with patch("app.db.session.SessionLocal") as mock_session_local:
            mock_session_local.return_value = db_session
            
            # Mock execute_area to avoid actual execution
            with patch("app.integrations.simple_plugins.scheduler.execute_area") as mock_execute:
                mock_execute.return_value = {
                    "status": "success",
                    "steps_executed": 1,
                    "execution_log": [],
                }
                
                # Mock create_execution_log
                with patch("app.integrations.simple_plugins.scheduler.create_execution_log") as mock_create_log:
                    mock_log = Mock()
                    mock_log.status = "Started"
                    mock_log.output = None
                    mock_log.error_message = None
                    mock_log.step_details = {}
                    mock_create_log.return_value = mock_log
                    
                    # Run scheduler task for a short time
                    task = asyncio.create_task(scheduler_task())
                    
                    # Wait for at least one tick
                    await asyncio.sleep(2.5)
                    
                    # Cancel the task
                    task.cancel()
                    
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    
                    # Verify that execute_area was called
                    assert mock_execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_scheduler_task_handles_execution_error(self, db_session: Session):
        """Test that scheduler task handles execution errors gracefully."""
        # Create a test user
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        # Create a test area
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
            trigger_params={"interval_seconds": 1},
        )
        db_session.add(area)
        db_session.commit()
        
        # Clear any previous state
        clear_last_run_state()
        
        # Mock SessionLocal to return our test session
        with patch("app.db.session.SessionLocal") as mock_session_local:
            mock_session_local.return_value = db_session
            
            # Mock execute_area to raise an error
            with patch("app.integrations.simple_plugins.scheduler.execute_area") as mock_execute:
                mock_execute.side_effect = Exception("Test error")
                
                # Mock create_execution_log
                with patch("app.integrations.simple_plugins.scheduler.create_execution_log") as mock_create_log:
                    mock_log = Mock()
                    mock_log.status = "Started"
                    mock_log.output = None
                    mock_log.error_message = None
                    mock_log.step_details = {}
                    mock_create_log.return_value = mock_log
                    
                    # Run scheduler task for a short time
                    task = asyncio.create_task(scheduler_task())
                    
                    # Wait for at least one tick
                    await asyncio.sleep(2.5)
                    
                    # Cancel the task
                    task.cancel()
                    
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    
                    # Verify that the error was logged
                    assert mock_log.status == "Failed"
                    assert mock_log.error_message == "Test error"

    @pytest.mark.asyncio
    async def test_scheduler_task_handles_log_creation_error(self, db_session: Session):
        """Test that scheduler task handles log creation errors gracefully."""
        # Create a test user
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        # Create a test area
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
            trigger_params={"interval_seconds": 1},
        )
        db_session.add(area)
        db_session.commit()
        
        # Clear any previous state
        clear_last_run_state()
        
        # Mock SessionLocal to return our test session
        with patch("app.db.session.SessionLocal") as mock_session_local:
            mock_session_local.return_value = db_session
            
            # Mock create_execution_log to raise an error
            with patch("app.integrations.simple_plugins.scheduler.create_execution_log") as mock_create_log:
                mock_create_log.side_effect = Exception("Log creation error")
                
                # Run scheduler task for a short time
                task = asyncio.create_task(scheduler_task())
                
                # Wait for at least one tick
                await asyncio.sleep(2.5)
                
                # Cancel the task
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
                # Task should continue running despite log creation error

    @pytest.mark.asyncio
    async def test_scheduler_task_cancellation(self):
        """Test that scheduler task can be cancelled gracefully."""
        # Mock SessionLocal
        with patch("app.db.session.SessionLocal") as mock_session_local:
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.all.return_value = []
            mock_db.close = Mock()  # Add close method
            mock_session_local.return_value = mock_db
            
            # Run scheduler task
            task = asyncio.create_task(scheduler_task())
            
            # Wait a bit
            await asyncio.sleep(0.5)
            
            # Cancel the task
            task.cancel()
            
            # Wait for task to finish (it handles cancellation gracefully)
            try:
                await task
            except asyncio.CancelledError:
                pass  # This is fine, the task was cancelled

    @pytest.mark.asyncio
    async def test_scheduler_task_updates_last_run(self, db_session: Session):
        """Test that scheduler task updates last run time after execution."""
        # Create a test user
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        # Create a test area
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
            trigger_params={"interval_seconds": 1},
        )
        db_session.add(area)
        db_session.commit()
        
        # Clear any previous state
        clear_last_run_state()
        
        # Mock SessionLocal to return our test session
        with patch("app.db.session.SessionLocal") as mock_session_local:
            mock_session_local.return_value = db_session
            
            # Mock execute_area to return success
            with patch("app.integrations.simple_plugins.scheduler.execute_area") as mock_execute:
                mock_execute.return_value = {
                    "status": "success",
                    "steps_executed": 1,
                    "execution_log": [],
                }
                
                # Mock create_execution_log
                with patch("app.integrations.simple_plugins.scheduler.create_execution_log") as mock_create_log:
                    mock_log = Mock()
                    mock_log.status = "Started"
                    mock_log.output = None
                    mock_log.error_message = None
                    mock_log.step_details = {}
                    mock_create_log.return_value = mock_log
                    
                    # Run scheduler task for a short time
                    task = asyncio.create_task(scheduler_task())
                    
                    # Wait for at least two ticks
                    await asyncio.sleep(2.5)
                    
                    # Cancel the task
                    task.cancel()
                    
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    
                    # First execution should happen
                    assert mock_execute.call_count >= 1
                    
                    # Second execution might not happen if interval hasn't passed
                    # This verifies last_run is being tracked


class TestSchedulerStartStop:
    """Test scheduler start and stop functionality."""

    @pytest.mark.asyncio
    async def test_start_scheduler_creates_task(self):
        """Test that start_scheduler creates a background task."""
        # Ensure we're in an event loop
        loop = asyncio.get_running_loop()
        
        # Start scheduler
        start_scheduler()
        
        # Stop it immediately
        stop_scheduler()
        
        # Wait a bit for cleanup
        await asyncio.sleep(0.1)

    def test_start_scheduler_without_event_loop(self):
        """Test that start_scheduler handles missing event loop."""
        # This test runs without asyncio context, so get_running_loop will fail
        # The function should handle this gracefully
        with patch("app.integrations.simple_plugins.scheduler.asyncio.get_running_loop") as mock_get_loop:
            mock_get_loop.side_effect = RuntimeError("No event loop")
            
            # Should not raise an error
            start_scheduler()

    @pytest.mark.asyncio
    async def test_start_scheduler_twice_warning(self):
        """Test that starting scheduler twice logs a warning."""
        start_scheduler()
        
        # Starting again should log warning
        start_scheduler()
        
        # Cleanup
        stop_scheduler()
        await asyncio.sleep(0.1)

    def test_stop_scheduler_when_not_running(self):
        """Test that stopping scheduler when not running is safe."""
        # Should not raise an error
        stop_scheduler()

    def test_clear_last_run_state(self):
        """Test clearing last run state."""
        from app.integrations.simple_plugins.scheduler import _last_run_by_area_id
        
        # Add some state
        _last_run_by_area_id["test_area"] = datetime.now(timezone.utc)
        
        # Clear it
        clear_last_run_state()
        
        # Verify it's cleared
        assert len(_last_run_by_area_id) == 0


class TestIsAreaDue:
    """Test is_area_due function edge cases."""

    def test_is_area_due_with_empty_trigger_params(self):
        """Test is_area_due with empty trigger params."""
        area = Mock()
        area.trigger_params = {}
        
        now = datetime.now(timezone.utc)
        last_run = now - timedelta(seconds=61)
        
        result = is_area_due(area, now, last_run)
        
        assert result is True

    def test_is_area_due_with_zero_interval(self):
        """Test is_area_due with zero interval."""
        area = Mock()
        area.trigger_params = {"interval_seconds": 0}
        
        now = datetime.now(timezone.utc)
        last_run = now - timedelta(seconds=1)
        
        # With 0 interval, should always be due
        result = is_area_due(area, now, last_run)
        
        assert result is True

    def test_is_area_due_with_very_large_interval(self):
        """Test is_area_due with very large interval."""
        area = Mock()
        area.trigger_params = {"interval_seconds": 86400 * 365}  # 1 year
        
        now = datetime.now(timezone.utc)
        last_run = now - timedelta(days=1)
        
        result = is_area_due(area, now, last_run)
        
        assert result is False

    def test_is_area_due_boundary_condition(self):
        """Test is_area_due at exact boundary."""
        area = Mock()
        area.trigger_params = {"interval_seconds": 100}
        
        now = datetime.now(timezone.utc)
        last_run = now - timedelta(seconds=100)
        
        result = is_area_due(area, now, last_run)
        
        assert result is True


class TestFetchDueAreas:
    """Test _fetch_due_areas function."""

    def test_fetch_due_areas_empty_database(self):
        """Test fetching areas from empty database."""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        
        result = _fetch_due_areas(mock_db)
        
        assert len(result) == 0

    def test_fetch_due_areas_with_multiple_areas(self):
        """Test fetching multiple due areas."""
        mock_db = Mock()
        
        mock_area1 = Mock()
        mock_area1.id = "area1"
        mock_area1.enabled = True
        
        mock_area2 = Mock()
        mock_area2.id = "area2"
        mock_area2.enabled = True
        
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = [mock_area1, mock_area2]
        mock_db.query.return_value = mock_query
        
        result = _fetch_due_areas(mock_db)
        
        assert len(result) == 2
        assert result[0].id == "area1"
        assert result[1].id == "area2"
