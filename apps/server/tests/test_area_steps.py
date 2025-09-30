"""Tests for AreaStep model and services."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.area import Area
from app.models.area_step import AreaStep
from app.schemas.area_step import AreaStepCreate, AreaStepUpdate
from app.services.area_steps import (
    AreaStepNotFoundError,
    DuplicateStepOrderError,
    create_area_step,
    delete_area_step,
    get_area_step_by_id,
    get_steps_by_area,
    reorder_area_steps,
    update_area_step,
)


def test_create_area_step(db_session: Session):
    """Test creating a new area step with valid data."""
    # Create a test area first
    user_id = uuid.uuid4()
    area = Area(
        user_id=user_id,
        name="Test Area",
        trigger_service="time",
        trigger_action="every_interval",
        reaction_service="debug",
        reaction_action="log",
        enabled=True,
    )
    db_session.add(area)
    db_session.commit()

    # Create a step
    step_in = AreaStepCreate(
        step_type="action",
        order=0,
        service="time",
        action="every_interval",
        config={"interval_seconds": 60},
    )
    step = create_area_step(db_session, area.id, step_in)

    assert step.id is not None
    assert step.area_id == area.id
    assert step.step_type == "action"
    assert step.order == 0
    assert step.service == "time"
    assert step.action == "every_interval"
    assert step.config == {"interval_seconds": 60}


def test_area_steps_ordering(db_session: Session):
    """Test that steps are returned in correct order."""
    # Create a test area
    user_id = uuid.uuid4()
    area = Area(
        user_id=user_id,
        name="Test Area",
        trigger_service="time",
        trigger_action="every_interval",
        reaction_service="debug",
        reaction_action="log",
        enabled=True,
    )
    db_session.add(area)
    db_session.commit()

    # Create steps in random order
    step2 = create_area_step(
        db_session,
        area.id,
        AreaStepCreate(step_type="reaction", order=2, service="email", action="send"),
    )
    step0 = create_area_step(
        db_session,
        area.id,
        AreaStepCreate(step_type="action", order=0, service="time", action="trigger"),
    )
    step1 = create_area_step(
        db_session,
        area.id,
        AreaStepCreate(step_type="condition", order=1, config={"expression": "x > 0"}),
    )

    # Fetch steps - should be ordered by order column
    steps = get_steps_by_area(db_session, area.id)

    assert len(steps) == 3
    assert steps[0].id == step0.id
    assert steps[0].order == 0
    assert steps[1].id == step1.id
    assert steps[1].order == 1
    assert steps[2].id == step2.id
    assert steps[2].order == 2


def test_duplicate_order_constraint(db_session: Session):
    """Test that duplicate order values in same area are not allowed."""
    # Create a test area
    user_id = uuid.uuid4()
    area = Area(
        user_id=user_id,
        name="Test Area",
        trigger_service="time",
        trigger_action="every_interval",
        reaction_service="debug",
        reaction_action="log",
        enabled=True,
    )
    db_session.add(area)
    db_session.commit()

    # Create first step with order=0
    create_area_step(
        db_session,
        area.id,
        AreaStepCreate(step_type="action", order=0, service="time", action="trigger"),
    )

    # Attempt to create another step with same order
    with pytest.raises(DuplicateStepOrderError) as exc_info:
        create_area_step(
            db_session,
            area.id,
            AreaStepCreate(step_type="reaction", order=0, service="email", action="send"),
        )

    assert str(area.id) in str(exc_info.value)
    assert "0" in str(exc_info.value)


def test_area_deletion_cascades_steps(db_session: Session):
    """Test that deleting an area cascades to its steps."""
    # Create a test area with steps
    user_id = uuid.uuid4()
    area = Area(
        user_id=user_id,
        name="Test Area",
        trigger_service="time",
        trigger_action="every_interval",
        reaction_service="debug",
        reaction_action="log",
        enabled=True,
    )
    db_session.add(area)
    db_session.commit()

    # Create multiple steps
    step1 = create_area_step(
        db_session,
        area.id,
        AreaStepCreate(step_type="action", order=0, service="time", action="trigger"),
    )
    step2 = create_area_step(
        db_session,
        area.id,
        AreaStepCreate(step_type="reaction", order=1, service="email", action="send"),
    )

    # Delete the area
    db_session.delete(area)
    db_session.commit()

    # Verify steps were cascade deleted
    assert get_area_step_by_id(db_session, step1.id) is None
    assert get_area_step_by_id(db_session, step2.id) is None


def test_step_type_validation():
    """Test that Pydantic schema validates step_type correctly."""
    # Valid step types
    valid_types = ["action", "reaction", "condition", "delay"]
    for step_type in valid_types:
        step = AreaStepCreate(step_type=step_type, order=0)
        assert step.step_type == step_type

    # Invalid step type should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        AreaStepCreate(step_type="invalid_type", order=0)

    assert "step_type must be one of" in str(exc_info.value)


def test_reorder_area_steps(db_session: Session):
    """Test reordering area steps."""
    # Create a test area
    user_id = uuid.uuid4()
    area = Area(
        user_id=user_id,
        name="Test Area",
        trigger_service="time",
        trigger_action="every_interval",
        reaction_service="debug",
        reaction_action="log",
        enabled=True,
    )
    db_session.add(area)
    db_session.commit()

    # Create steps in order 0, 1, 2
    step0 = create_area_step(
        db_session,
        area.id,
        AreaStepCreate(step_type="action", order=0, service="time", action="trigger"),
    )
    step1 = create_area_step(
        db_session,
        area.id,
        AreaStepCreate(step_type="condition", order=1, config={"expression": "x > 0"}),
    )
    step2 = create_area_step(
        db_session,
        area.id,
        AreaStepCreate(step_type="reaction", order=2, service="email", action="send"),
    )

    # Reorder: step2 -> step0 -> step1 (reverse of middle two)
    new_order = [step2.id, step0.id, step1.id]
    reordered_steps = reorder_area_steps(db_session, area.id, new_order)

    assert len(reordered_steps) == 3
    assert reordered_steps[0].id == step2.id
    assert reordered_steps[0].order == 0
    assert reordered_steps[1].id == step0.id
    assert reordered_steps[1].order == 1
    assert reordered_steps[2].id == step1.id
    assert reordered_steps[2].order == 2

    # Verify order persisted in database
    db_steps = get_steps_by_area(db_session, area.id)
    assert db_steps[0].id == step2.id
    assert db_steps[1].id == step0.id
    assert db_steps[2].id == step1.id


def test_reorder_area_steps_wrong_area(db_session: Session):
    """Test that reordering fails if step doesn't belong to the area."""
    # Create two areas
    user_id = uuid.uuid4()
    area1 = Area(
        user_id=user_id,
        name="Area 1",
        trigger_service="time",
        trigger_action="every_interval",
        reaction_service="debug",
        reaction_action="log",
        enabled=True,
    )
    area2 = Area(
        user_id=user_id,
        name="Area 2",
        trigger_service="time",
        trigger_action="every_interval",
        reaction_service="debug",
        reaction_action="log",
        enabled=True,
    )
    db_session.add_all([area1, area2])
    db_session.commit()

    # Create step in area1
    step1 = create_area_step(
        db_session,
        str(area1.id),
        AreaStepCreate(step_type="action", order=0, service="time", action="trigger"),
    )

    # Try to reorder area2 with step from area1
    with pytest.raises(AreaStepNotFoundError):
        reorder_area_steps(db_session, str(area2.id), [step1.id])


def test_step_config_jsonb_storage(db_session: Session):
    """Test that JSONB config field stores complex data correctly."""
    # Create a test area
    user_id = uuid.uuid4()
    area = Area(
        user_id=user_id,
        name="Test Area",
        trigger_service="time",
        trigger_action="every_interval",
        reaction_service="debug",
        reaction_action="log",
        enabled=True,
    )
    db_session.add(area)
    db_session.commit()

    # Create step with complex config
    complex_config = {
        "interval_seconds": 60,
        "nested": {"key": "value", "list": [1, 2, 3]},
        "boolean": True,
        "null_value": None,
    }

    step = create_area_step(
        db_session,
        area.id,
        AreaStepCreate(
            step_type="delay",
            order=0,
            config=complex_config,
        ),
    )

    # Fetch step and verify config
    fetched_step = get_area_step_by_id(db_session, step.id)
    assert fetched_step is not None
    assert fetched_step.config == complex_config
    assert fetched_step.config["nested"]["list"] == [1, 2, 3]


def test_update_area_step(db_session: Session):
    """Test updating an existing area step."""
    # Create a test area with a step
    user_id = uuid.uuid4()
    area = Area(
        user_id=user_id,
        name="Test Area",
        trigger_service="time",
        trigger_action="every_interval",
        reaction_service="debug",
        reaction_action="log",
        enabled=True,
    )
    db_session.add(area)
    db_session.commit()

    step = create_area_step(
        db_session,
        area.id,
        AreaStepCreate(step_type="action", order=0, service="time", action="trigger"),
    )

    # Update the step
    update_data = AreaStepUpdate(
        step_type="reaction",
        service="email",
        action="send",
        config={"to": "test@example.com"},
    )
    updated_step = update_area_step(db_session, step.id, update_data)

    assert updated_step.step_type == "reaction"
    assert updated_step.service == "email"
    assert updated_step.action == "send"
    assert updated_step.config == {"to": "test@example.com"}
    assert updated_step.order == 0  # Should remain unchanged


def test_update_nonexistent_step(db_session: Session):
    """Test that updating a nonexistent step raises an error."""
    fake_id = uuid.uuid4()
    update_data = AreaStepUpdate(step_type="action")

    with pytest.raises(AreaStepNotFoundError):
        update_area_step(db_session, fake_id, update_data)


def test_delete_area_step(db_session: Session):
    """Test deleting an area step."""
    # Create a test area with a step
    user_id = uuid.uuid4()
    area = Area(
        user_id=user_id,
        name="Test Area",
        trigger_service="time",
        trigger_action="every_interval",
        reaction_service="debug",
        reaction_action="log",
        enabled=True,
    )
    db_session.add(area)
    db_session.commit()

    step = create_area_step(
        db_session,
        area.id,
        AreaStepCreate(step_type="action", order=0, service="time", action="trigger"),
    )

    # Delete the step
    result = delete_area_step(db_session, step.id)
    assert result is True

    # Verify step was deleted
    assert get_area_step_by_id(db_session, step.id) is None


def test_delete_nonexistent_step(db_session: Session):
    """Test that deleting a nonexistent step returns False."""
    fake_id = uuid.uuid4()
    result = delete_area_step(db_session, fake_id)
    assert result is False
