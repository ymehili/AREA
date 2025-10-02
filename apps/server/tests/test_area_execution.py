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