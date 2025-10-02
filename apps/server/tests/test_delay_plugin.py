"""Unit tests for the delay plugin."""

import asyncio
import time
from unittest.mock import AsyncMock, Mock

import pytest

from app.integrations.simple_plugins.delay_plugin import delay_handler


@pytest.mark.asyncio
async def test_delay_handler_seconds():
    """Test delay handler with seconds unit."""
    # Create mock area object
    mock_area = Mock()
    mock_area.id = "test-area-id"
    mock_area.user_id = "test-user-id"
    
    # Set up parameters for 0.1 seconds delay
    params = {
        "duration": 0.1,
        "unit": "seconds"
    }
    
    event = {
        "now": "2023-01-01T00:00:00Z",
        "area_id": "test-area-id",
        "user_id": "test-user-id",
        "tick": True
    }
    
    # Record start time
    start_time = time.time()
    
    # Call the handler
    await delay_handler(mock_area, params, event)
    
    # Record end time
    end_time = time.time()
    
    # Check that the delay was approximately 0.1 seconds
    elapsed_time = end_time - start_time
    assert 0.08 <= elapsed_time <= 0.15, f"Expected ~0.1s delay, but got {elapsed_time}s"


@pytest.mark.asyncio
async def test_delay_handler_minutes():
    """Test delay handler with minutes unit."""
    # Create mock area object
    mock_area = Mock()
    mock_area.id = "test-area-id"
    mock_area.user_id = "test-user-id"
    
    # Set up parameters for 0.01 minutes delay (0.6 seconds)
    params = {
        "duration": 0.01,
        "unit": "minutes"
    }
    
    event = {
        "now": "2023-01-01T00:00:00Z",
        "area_id": "test-area-id",
        "user_id": "test-user-id",
        "tick": True
    }
    
    # Record start time
    start_time = time.time()
    
    # Call the handler
    await delay_handler(mock_area, params, event)
    
    # Record end time
    end_time = time.time()
    
    # Check that the delay was approximately 0.6 seconds (0.01 minutes)
    elapsed_time = end_time - start_time
    expected_time = 0.01 * 60  # 0.01 minutes = 0.6 seconds
    assert expected_time * 0.8 <= elapsed_time <= expected_time * 1.5, f"Expected ~{expected_time}s delay, but got {elapsed_time}s"


@pytest.mark.asyncio
async def test_delay_handler_hours():
    """Test delay handler with hours unit."""
    # Create mock area object
    mock_area = Mock()
    mock_area.id = "test-area-id"
    mock_area.user_id = "test-user-id"
    
    # Set up parameters for 0.0001 hours delay (0.36 seconds)
    params = {
        "duration": 0.0001,
        "unit": "hours"
    }
    
    event = {
        "now": "2023-01-01T00:00:00Z",
        "area_id": "test-area-id",
        "user_id": "test-user-id",
        "tick": True
    }
    
    # Record start time
    start_time = time.time()
    
    # Call the handler
    await delay_handler(mock_area, params, event)
    
    # Record end time
    end_time = time.time()
    
    # Check that the delay was approximately 0.36 seconds (0.0001 hours)
    elapsed_time = end_time - start_time
    expected_time = 0.0001 * 60 * 60  # 0.0001 hours = 0.36 seconds
    assert expected_time * 0.8 <= elapsed_time <= expected_time * 1.5, f"Expected ~{expected_time}s delay, but got {elapsed_time}s"


@pytest.mark.asyncio
async def test_delay_handler_days():
    """Test delay handler with days unit."""
    # Create mock area object
    mock_area = Mock()
    mock_area.id = "test-area-id"
    mock_area.user_id = "test-user-id"
    
    # Set up parameters for 0.000001 days delay (0.0864 seconds)
    params = {
        "duration": 0.000001,
        "unit": "days"
    }
    
    event = {
        "now": "2023-01-01T00:00:00Z",
        "area_id": "test-area-id",
        "user_id": "test-user-id",
        "tick": True
    }
    
    # Record start time
    start_time = time.time()
    
    # Call the handler
    await delay_handler(mock_area, params, event)
    
    # Record end time
    end_time = time.time()
    
    # Check that the delay was approximately 0.0864 seconds (0.000001 days)
    elapsed_time = end_time - start_time
    expected_time = 0.000001 * 60 * 60 * 24  # 0.000001 days = 0.0864 seconds
    assert expected_time * 0.8 <= elapsed_time <= expected_time * 1.5, f"Expected ~{expected_time}s delay, but got {elapsed_time}s"


@pytest.mark.asyncio
async def test_delay_handler_defaults_to_seconds():
    """Test delay handler defaults to seconds when invalid unit is provided."""
    # Create mock area object
    mock_area = Mock()
    mock_area.id = "test-area-id"
    mock_area.user_id = "test-user-id"
    
    # Set up parameters with invalid unit, should default to seconds
    params = {
        "duration": 0.1,
        "unit": "invalid_unit"
    }
    
    event = {
        "now": "2023-01-01T00:00:00Z",
        "area_id": "test-area-id",
        "user_id": "test-user-id",
        "tick": True
    }
    
    # Record start time
    start_time = time.time()
    
    # Call the handler
    await delay_handler(mock_area, params, event)
    
    # Record end time
    end_time = time.time()
    
    # Check that the delay was approximately 0.1 seconds
    elapsed_time = end_time - start_time
    assert 0.08 <= elapsed_time <= 0.15, f"Expected ~0.1s delay, but got {elapsed_time}s"


@pytest.mark.asyncio
async def test_delay_handler_defaults_missing_unit():
    """Test delay handler defaults to seconds when unit is missing."""
    # Create mock area object
    mock_area = Mock()
    mock_area.id = "test-area-id"
    mock_area.user_id = "test-user-id"
    
    # Set up parameters with missing unit, should default to seconds
    params = {
        "duration": 0.1
        # No unit provided, should default to seconds
    }
    
    event = {
        "now": "2023-01-01T00:00:00Z",
        "area_id": "test-area-id",
        "user_id": "test-user-id",
        "tick": True
    }
    
    # Record start time
    start_time = time.time()
    
    # Call the handler
    await delay_handler(mock_area, params, event)
    
    # Record end time
    end_time = time.time()
    
    # Check that the delay was approximately 0.1 seconds
    elapsed_time = end_time - start_time
    assert 0.08 <= elapsed_time <= 0.15, f"Expected ~0.1s delay, but got {elapsed_time}s"


@pytest.mark.asyncio
async def test_delay_handler_defaults_missing_duration():
    """Test delay handler defaults duration to 1 second when missing."""
    # Create mock area object
    mock_area = Mock()
    mock_area.id = "test-area-id"
    mock_area.user_id = "test-user-id"
    
    # Set up parameters with missing duration, should default to 1 second
    params = {
        "unit": "seconds"
        # No duration provided, should default to 1
    }
    
    event = {
        "now": "2023-01-01T00:00:00Z",
        "area_id": "test-area-id",
        "user_id": "test-user-id",
        "tick": True
    }
    
    # Record start time
    start_time = time.time()
    
    # Call the handler
    await delay_handler(mock_area, params, event)
    
    # Record end time
    end_time = time.time()
    
    # Check that the delay was approximately 1 second
    elapsed_time = end_time - start_time
    assert 0.8 <= elapsed_time <= 1.5, f"Expected ~1s delay, but got {elapsed_time}s"