"""Integration tests for the area scheduler."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.integrations.simple_plugins.scheduler import is_area_due
from app.models.area import Area
from app.models.area_step import AreaStep, AreaStepType


def test_is_area_due_with_real_area(db_session: Session):
    """Test is_area_due function with a real Area object."""
    # Create a simple area with steps for testing
    user_id = uuid.uuid4()
    area = Area(
        user_id=user_id,
        name="Due Test Area",
        enabled=True,
    )
    db_session.add(area)
    db_session.flush()

    # Add ACTION step (time trigger)
    action_step = AreaStep(
        area_id=area.id,
        position=0,
        step_type=AreaStepType.ACTION,
        service_slug="time",
        action_key="every_interval",
        config={"interval_seconds": 60},
    )
    db_session.add(action_step)

    # Add REACTION step (debug log)
    reaction_step = AreaStep(
        area_id=area.id,
        position=1,
        step_type=AreaStepType.REACTION,
        service_slug="debug",
        action_key="log",
        config={},
    )
    db_session.add(reaction_step)
    db_session.commit()
    db_session.refresh(area)

    now = datetime.now(timezone.utc)

    # First run - should be due
    assert is_area_due(area, now, None) is True

    # Just ran - should not be due
    assert is_area_due(area, now, now) is False