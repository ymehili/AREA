"""Integration tests for multi-step area execution with delay steps."""

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.area import Area
from app.models.area_step import AreaStep
from app.services.area_execution import execute_area_steps
from app.services.area_steps import get_steps_by_area
from app.services.execution_logs import create_execution_log


@pytest.mark.asyncio
async def test_execute_area_with_single_delay_step():
    """Test executing an area with a single delay step."""
    # Create mock database session
    mock_db = Mock(spec=Session)
    
    # Create mock area
    mock_area = Mock(spec=Area)
    mock_area.id = uuid.uuid4()
    mock_area.user_id = uuid.uuid4()
    
    # Create a delay step
    delay_step = AreaStep(
        id="step-1",
        area_id=mock_area.id,
        step_type="delay",
        order=0,
        service=None,
        action=None,
        config={"duration": 0.01, "unit": "seconds"}  # Very short delay for tests
    )
    
    # Mock the get_steps_by_area function to return our delay step
    with patch('app.services.area_execution.get_steps_by_area', return_value=[delay_step]):
        with patch('app.services.area_execution.create_execution_log') as mock_create_log:
            # Mock return value for create_execution_log with proper structure
            mock_execution_log = Mock()
            mock_execution_log.step_details = {}
            mock_execution_log.status = "Started"
            mock_create_log.return_value = mock_execution_log
            # Event data
            event = {
                "now": datetime.now(timezone.utc).isoformat(),
                "area_id": str(mock_area.id),
                "user_id": str(mock_area.user_id),
                "tick": True
            }
            
            # Execute the area
            result = await execute_area_steps(mock_db, mock_area, event)
            
            # Should complete successfully
            assert result is True


@pytest.mark.asyncio
async def test_execute_area_with_multiple_steps_including_delay():
    """Test executing an area with multiple steps including a delay."""
    # Create mock database session
    mock_db = Mock(spec=Session)
    
    # Create mock area
    mock_area = Mock(spec=Area)
    mock_area.id = uuid.uuid4()
    mock_area.user_id = uuid.uuid4()
    
    # Create steps: trigger -> delay -> reaction
    trigger_step = AreaStep(
        id="step-1",
        area_id=mock_area.id,
        step_type="trigger",
        order=0,
        service="time",
        action="every_interval",
        config={"interval_seconds": 60}
    )
    
    delay_step = AreaStep(
        id="step-2",
        area_id=mock_area.id,
        step_type="delay",
        order=1,
        service=None,
        action=None,
        config={"duration": 0.01, "unit": "seconds"}  # Very short delay for tests
    )
    
    reaction_step = AreaStep(
        id="step-3",
        area_id=mock_area.id,
        step_type="reaction",
        order=2,
        service="debug",
        action="log",
        config={"message": "Test message after delay"}
    )
    
    steps = [trigger_step, delay_step, reaction_step]
    
    # Mock the get_steps_by_area function to return our steps
    with patch('app.services.area_execution.get_steps_by_area', return_value=steps):
        with patch('app.services.area_execution.create_execution_log') as mock_create_log:
            # Mock return value for create_execution_log with proper structure
            mock_execution_log = Mock()
            mock_execution_log.step_details = {}
            mock_execution_log.status = "Started"
            mock_create_log.return_value = mock_execution_log
            # Mock the reaction handler
            with patch('app.services.area_execution.ExecutionEngine._execute_action_reaction_step') as mock_exec_action:
                mock_exec_action.return_value = None  # Mock implementation
                
                # Event data
                event = {
                    "now": datetime.now(timezone.utc).isoformat(),
                    "area_id": str(mock_area.id),
                    "user_id": str(mock_area.user_id),
                    "tick": True
                }
                
                # Execute the area
                result = await execute_area_steps(mock_db, mock_area, event)
                
                # Should complete successfully
                assert result is True
                
                # Verify that all steps were processed
                mock_exec_action.assert_called()


@pytest.mark.asyncio
async def test_execute_area_delay_with_different_units():
    """Test executing an area with delay steps using different time units."""
    # Create mock database session
    mock_db = Mock(spec=Session)
    
    # Create mock area
    mock_area = Mock(spec=Area)
    mock_area.id = uuid.uuid4()
    mock_area.user_id = uuid.uuid4()
    
    # Create delay steps with different units
    delay_seconds = AreaStep(
        id="step-1",
        area_id=mock_area.id,
        step_type="delay",
        order=0,
        service=None,
        action=None,
        config={"duration": 0.01, "unit": "seconds"}
    )
    
    delay_minutes = AreaStep(
        id="step-2",
        area_id=mock_area.id,
        step_type="delay",
        order=1,
        service=None,
        action=None,
        config={"duration": 0.0001, "unit": "minutes"}  # Very short for tests
    )
    
    steps = [delay_seconds, delay_minutes]
    
    # Mock the get_steps_by_area function to return our steps
    with patch('app.services.area_execution.get_steps_by_area', return_value=steps):
        with patch('app.services.area_execution.create_execution_log') as mock_create_log:
            # Mock return value for create_execution_log with proper structure
            mock_execution_log = Mock()
            mock_execution_log.step_details = {}
            mock_execution_log.status = "Started"
            mock_create_log.return_value = mock_execution_log
            # Event data
            event = {
                "now": datetime.now(timezone.utc).isoformat(),
                "area_id": str(mock_area.id),
                "user_id": str(mock_area.user_id),
                "tick": True
            }
            
            # Execute the area
            result = await execute_area_steps(mock_db, mock_area, event)
            
            # Should complete successfully
            assert result is True


@pytest.mark.asyncio
async def test_execute_area_delay_defaults():
    """Test executing an area with delay steps using default values."""
    # Create mock database session
    mock_db = Mock(spec=Session)
    
    # Create mock area
    mock_area = Mock(spec=Area)
    mock_area.id = uuid.uuid4()
    mock_area.user_id = uuid.uuid4()
    
    # Create delay step with minimal config (defaults should apply)
    delay_step = AreaStep(
        id="step-1",
        area_id=mock_area.id,
        step_type="delay",
        order=0,
        service=None,
        action=None,
        config={}  # Empty config, should default to 1 second
    )
    
    # Create delay step with invalid unit (should default to seconds)
    delay_invalid_unit = AreaStep(
        id="step-2",
        area_id=mock_area.id,
        step_type="delay",
        order=1,
        service=None,
        action=None,
        config={"duration": 0.1, "unit": "invalid_unit"}
    )
    
    steps = [delay_step, delay_invalid_unit]
    
    # Mock the get_steps_by_area function to return our steps
    with patch('app.services.area_execution.get_steps_by_area', return_value=steps):
        with patch('app.services.area_execution.create_execution_log') as mock_create_log:
            # Mock return value for create_execution_log with proper structure
            mock_execution_log = Mock()
            mock_execution_log.step_details = {}
            mock_execution_log.status = "Started"
            mock_create_log.return_value = mock_execution_log
            # Event data
            event = {
                "now": datetime.now(timezone.utc).isoformat(),
                "area_id": str(mock_area.id),
                "user_id": str(mock_area.user_id),
                "tick": True
            }
            
            # Execute the area
            result = await execute_area_steps(mock_db, mock_area, event)
            
            # Should complete successfully
            assert result is True


@pytest.mark.asyncio
async def test_execute_area_delay_missing_config():
    """Test executing an area with delay steps with missing config."""
    # Create mock database session
    mock_db = Mock(spec=Session)
    
    # Create mock area
    mock_area = Mock(spec=Area)
    mock_area.id = uuid.uuid4()
    mock_area.user_id = uuid.uuid4()
    
    # Create delay step with no config (should default)
    delay_step = AreaStep(
        id="step-1",
        area_id=mock_area.id,
        step_type="delay",
        order=0,
        service=None,
        action=None,
        config=None  # No config at all
    )
    
    steps = [delay_step]
    
    # Mock the get_steps_by_area function to return our step
    with patch('app.services.area_execution.get_steps_by_area', return_value=steps):
        with patch('app.services.area_execution.create_execution_log') as mock_create_log:
            # Mock return value for create_execution_log with proper structure
            mock_execution_log = Mock()
            mock_execution_log.step_details = {}
            mock_execution_log.status = "Started"
            mock_create_log.return_value = mock_execution_log
            # Event data
            event = {
                "now": datetime.now(timezone.utc).isoformat(),
                "area_id": str(mock_area.id),
                "user_id": str(mock_area.user_id),
                "tick": True
            }
            
            # Execute the area
            result = await execute_area_steps(mock_db, mock_area, event)
            
            # Should complete successfully
            assert result is True


@pytest.mark.asyncio
async def test_execute_area_with_no_steps():
    """Test executing an area with no steps returns True."""
    mock_db = Mock(spec=Session)
    
    mock_area = Mock(spec=Area)
    mock_area.id = uuid.uuid4()
    mock_area.user_id = uuid.uuid4()
    
    # Mock get_steps_by_area to return empty list
    with patch('app.services.area_execution.get_steps_by_area', return_value=[]):
        event = {"tick": True}
        
        result = await execute_area_steps(mock_db, mock_area, event)
        
        # Should complete successfully even with no steps
        assert result is True


@pytest.mark.asyncio
async def test_execute_area_with_unknown_step_type():
    """Test executing an area with unknown step type fails gracefully."""
    mock_db = Mock(spec=Session)
    
    mock_area = Mock(spec=Area)
    mock_area.id = uuid.uuid4()
    mock_area.user_id = uuid.uuid4()
    
    # Create step with unknown type
    unknown_step = AreaStep(
        id="step-1",
        area_id=mock_area.id,
        step_type="unknown_type",
        order=0,
        service="test",
        action="test",
        config={}
    )
    
    with patch('app.services.area_execution.get_steps_by_area', return_value=[unknown_step]):
        with patch('app.services.area_execution.create_execution_log') as mock_create_log:
            mock_execution_log = Mock()
            mock_execution_log.step_details = {}
            mock_execution_log.status = "Started"
            mock_create_log.return_value = mock_execution_log
            
            event = {"tick": True}
            
            result = await execute_area_steps(mock_db, mock_area, event)
            
            # Should fail for unknown step type
            assert result is False
            assert mock_execution_log.status == "Failed"
            assert "Unknown step type" in mock_execution_log.error_message


@pytest.mark.asyncio
async def test_execute_area_with_exception():
    """Test executing an area that raises an exception."""
    mock_db = Mock(spec=Session)
    
    mock_area = Mock(spec=Area)
    mock_area.id = uuid.uuid4()
    mock_area.user_id = uuid.uuid4()
    
    delay_step = AreaStep(
        id="step-1",
        area_id=mock_area.id,
        step_type="delay",
        order=0,
        service=None,
        action=None,
        config={"duration": 1, "unit": "seconds"}
    )
    
    with patch('app.services.area_execution.get_steps_by_area', return_value=[delay_step]):
        with patch('app.services.area_execution.create_execution_log') as mock_create_log:
            mock_execution_log = Mock()
            mock_execution_log.step_details = {}
            mock_execution_log.status = "Started"
            mock_create_log.return_value = mock_execution_log
            
            # Make asyncio.sleep raise an exception
            with patch('asyncio.sleep', side_effect=Exception("Test error")):
                event = {"tick": True}
                
                result = await execute_area_steps(mock_db, mock_area, event)
                
                # Should return False on exception
                assert result is False
                assert mock_execution_log.status == "Failed"
                assert "Test error" in mock_execution_log.error_message


@pytest.mark.asyncio
async def test_execute_delay_step_with_wrong_type():
    """Test _execute_delay_step raises ValueError for wrong step type."""
    from app.services.area_execution import ExecutionEngine
    
    mock_db = Mock(spec=Session)
    engine = ExecutionEngine(mock_db)
    
    mock_area = Mock(spec=Area)
    mock_area.id = uuid.uuid4()
    mock_area.user_id = uuid.uuid4()
    
    # Create a non-delay step
    action_step = AreaStep(
        id="step-1",
        area_id=mock_area.id,
        step_type="action",
        order=0,
        service="test",
        action="test",
        config={}
    )
    
    with pytest.raises(ValueError, match="Expected delay step"):
        await engine._execute_delay_step(mock_area, action_step, {})


@pytest.mark.asyncio
async def test_execute_delay_step_with_hours_unit():
    """Test delay step with hours unit."""
    from app.services.area_execution import ExecutionEngine
    
    mock_db = Mock(spec=Session)
    engine = ExecutionEngine(mock_db)
    
    mock_area = Mock(spec=Area)
    mock_area.id = uuid.uuid4()
    mock_area.user_id = uuid.uuid4()
    
    delay_step = AreaStep(
        id="step-1",
        area_id=mock_area.id,
        step_type="delay",
        order=0,
        service=None,
        action=None,
        config={"duration": 0.0001, "unit": "hours"}
    )
    
    await engine._execute_delay_step(mock_area, delay_step, {})
    # If it completes without error, the test passes


@pytest.mark.asyncio
async def test_execute_delay_step_with_days_unit():
    """Test delay step with days unit."""
    from app.services.area_execution import ExecutionEngine
    
    mock_db = Mock(spec=Session)
    engine = ExecutionEngine(mock_db)
    
    mock_area = Mock(spec=Area)
    mock_area.id = uuid.uuid4()
    mock_area.user_id = uuid.uuid4()
    
    delay_step = AreaStep(
        id="step-1",
        area_id=mock_area.id,
        step_type="delay",
        order=0,
        service=None,
        action=None,
        config={"duration": 0.00001, "unit": "days"}
    )
    
    await engine._execute_delay_step(mock_area, delay_step, {})
    # If it completes without error, the test passes


@pytest.mark.asyncio
async def test_execute_delay_step_with_unknown_unit():
    """Test delay step with unknown unit defaults to seconds."""
    from app.services.area_execution import ExecutionEngine
    
    mock_db = Mock(spec=Session)
    engine = ExecutionEngine(mock_db)
    
    mock_area = Mock(spec=Area)
    mock_area.id = uuid.uuid4()
    mock_area.user_id = uuid.uuid4()
    
    delay_step = AreaStep(
        id="step-1",
        area_id=mock_area.id,
        step_type="delay",
        order=0,
        service=None,
        action=None,
        config={"duration": 0.01, "unit": "unknown_unit"}
    )
    
    # Should log warning but not fail
    await engine._execute_delay_step(mock_area, delay_step, {})


@pytest.mark.asyncio
async def test_execute_action_reaction_step():
    """Test executing action/reaction step."""
    from app.services.area_execution import ExecutionEngine
    
    mock_db = Mock(spec=Session)
    engine = ExecutionEngine(mock_db)
    
    mock_area = Mock(spec=Area)
    mock_area.id = uuid.uuid4()
    mock_area.user_id = uuid.uuid4()
    
    action_step = AreaStep(
        id="step-1",
        area_id=mock_area.id,
        step_type="action",
        order=0,
        service="debug",
        action="log",
        config={"message": "Test"}
    )
    
    # Mock the registry and handler
    mock_handler = Mock()
    with patch.object(engine.registry, 'get_reaction_handler', return_value=mock_handler):
        event = {"tick": True}
        
        await engine._execute_action_reaction_step(mock_area, action_step, event)
        
        # Verify handler was called
        mock_handler.assert_called_once()
        call_args = mock_handler.call_args[0]
        assert call_args[0] == mock_area
        assert "message" in call_args[1]
        assert call_args[1]["message"] == "Test"
        assert call_args[1]["area_id"] == str(mock_area.id)
        assert call_args[1]["user_id"] == str(mock_area.user_id)


@pytest.mark.asyncio
async def test_execute_action_reaction_step_wrong_type():
    """Test _execute_action_reaction_step raises ValueError for wrong step type."""
    from app.services.area_execution import ExecutionEngine
    
    mock_db = Mock(spec=Session)
    engine = ExecutionEngine(mock_db)
    
    mock_area = Mock(spec=Area)
    mock_area.id = uuid.uuid4()
    mock_area.user_id = uuid.uuid4()
    
    delay_step = AreaStep(
        id="step-1",
        area_id=mock_area.id,
        step_type="delay",
        order=0,
        service=None,
        action=None,
        config={}
    )
    
    with pytest.raises(ValueError, match="Expected action or reaction step"):
        await engine._execute_action_reaction_step(mock_area, delay_step, {})


@pytest.mark.asyncio
async def test_execute_action_reaction_step_missing_service():
    """Test _execute_action_reaction_step raises ValueError for missing service."""
    from app.services.area_execution import ExecutionEngine
    
    mock_db = Mock(spec=Session)
    engine = ExecutionEngine(mock_db)
    
    mock_area = Mock(spec=Area)
    mock_area.id = uuid.uuid4()
    mock_area.user_id = uuid.uuid4()
    
    action_step = AreaStep(
        id="step-1",
        area_id=mock_area.id,
        step_type="action",
        order=0,
        service=None,
        action="log",
        config={}
    )
    
    with pytest.raises(ValueError, match="missing service or action"):
        await engine._execute_action_reaction_step(mock_area, action_step, {})


@pytest.mark.asyncio
async def test_execute_action_reaction_step_missing_action():
    """Test _execute_action_reaction_step raises ValueError for missing action."""
    from app.services.area_execution import ExecutionEngine
    
    mock_db = Mock(spec=Session)
    engine = ExecutionEngine(mock_db)
    
    mock_area = Mock(spec=Area)
    mock_area.id = uuid.uuid4()
    mock_area.user_id = uuid.uuid4()
    
    action_step = AreaStep(
        id="step-1",
        area_id=mock_area.id,
        step_type="action",
        order=0,
        service="debug",
        action=None,
        config={}
    )
    
    with pytest.raises(ValueError, match="missing service or action"):
        await engine._execute_action_reaction_step(mock_area, action_step, {})


@pytest.mark.asyncio
async def test_execute_action_reaction_step_no_handler():
    """Test _execute_action_reaction_step raises ValueError when no handler found."""
    from app.services.area_execution import ExecutionEngine
    
    mock_db = Mock(spec=Session)
    engine = ExecutionEngine(mock_db)
    
    mock_area = Mock(spec=Area)
    mock_area.id = uuid.uuid4()
    mock_area.user_id = uuid.uuid4()
    
    action_step = AreaStep(
        id="step-1",
        area_id=mock_area.id,
        step_type="action",
        order=0,
        service="nonexistent",
        action="nonexistent",
        config={}
    )
    
    # Mock registry to return None (no handler)
    with patch.object(engine.registry, 'get_reaction_handler', return_value=None):
        with pytest.raises(ValueError, match="No handler found"):
            await engine._execute_action_reaction_step(mock_area, action_step, {})


@pytest.mark.asyncio
async def test_area_execution_state_with_custom_start_time():
    """Test AreaExecutionState with custom start_time."""
    from app.services.area_execution import AreaExecutionState
    
    custom_time = datetime.now(timezone.utc)
    area_id = str(uuid.uuid4())
    
    state = AreaExecutionState(area_id, current_step_index=2, start_time=custom_time)
    
    assert state.area_id == area_id
    assert state.current_step_index == 2
    assert state.start_time == custom_time


@pytest.mark.asyncio
async def test_area_execution_state_default_start_time():
    """Test AreaExecutionState with default start_time."""
    from app.services.area_execution import AreaExecutionState
    
    area_id = str(uuid.uuid4())
    
    state = AreaExecutionState(area_id)
    
    assert state.area_id == area_id
    assert state.current_step_index == 0
    assert state.start_time is not None