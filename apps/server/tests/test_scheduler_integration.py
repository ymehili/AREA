"""Integration tests for the area scheduler."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.integrations.simple_plugins.scheduler import is_area_due
from app.models.area import Area


def test_is_area_due_with_real_area(db_session: Session):
    """Test is_area_due function with a real Area object."""
    # Create a simple area for testing
    user_id = uuid.uuid4()
    area = Area(
        user_id=user_id,
        name="Due Test Area",
        trigger_service="time",
        trigger_action="every_interval",
        trigger_params={"interval_seconds": 60},
        reaction_service="debug",
        reaction_action="log",
        enabled=True,
    )

    now = datetime.now(timezone.utc)

    # First run - should be due
    assert is_area_due(area, now, None) is True

    # Just ran - should not be due
    assert is_area_due(area, now, now) is False