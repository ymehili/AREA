"""Tests for area service layer with multi-step workflows."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.area import AreaCreate, AreaUpdate, AreaStepCreate
from app.services.areas import (
    create_area,
    get_area_by_id,
    get_areas_by_user,
    update_area,
    delete_area,
    DuplicateAreaError,
    AreaNotFoundError,
)


def test_create_area_with_multi_step_workflow(db_session: Session):
    """Test creating an area with multiple steps."""
    # Create a test user
    user = User(email="test@example.com", hashed_password="fake_hash")
    db_session.add(user)
    db_session.commit()

    # Create area with multiple steps
    area_data = AreaCreate(
        name="Multi-step Area",
        steps=[
            AreaStepCreate(
                position=0,
                step_type="action",
                service_slug="time",
                action_key="every_interval",
                config={"interval_seconds": 120},
            ),
            AreaStepCreate(
                position=1,
                step_type="reaction",
                service_slug="debug",
                action_key="log",
                config={"message": "Step 1 executed"},
            ),
            AreaStepCreate(
                position=2,
                step_type="delay",
                config={"seconds": 30},
            ),
            AreaStepCreate(
                position=3,
                step_type="reaction",
                service_slug="debug",
                action_key="log",
                config={"message": "Step 3 executed"},
            ),
        ],
    )

    area = create_area(db_session, area_data, str(user.id))

    # Verify area was created
    assert area.id is not None
    assert area.name == "Multi-step Area"
    assert area.user_id == user.id
    assert area.enabled is True

    # Verify steps were created correctly
    assert len(area.steps) == 4

    # Check ACTION step
    assert area.steps[0].position == 0
    assert area.steps[0].step_type.value == "action"
    assert area.steps[0].service_slug == "time"
    assert area.steps[0].action_key == "every_interval"
    assert area.steps[0].config == {"interval_seconds": 120}

    # Check first REACTION step
    assert area.steps[1].position == 1
    assert area.steps[1].step_type.value == "reaction"
    assert area.steps[1].service_slug == "debug"
    assert area.steps[1].action_key == "log"

    # Check DELAY step
    assert area.steps[2].position == 2
    assert area.steps[2].step_type.value == "delay"
    assert area.steps[2].service_slug is None
    assert area.steps[2].action_key is None
    assert area.steps[2].config == {"seconds": 30}

    # Check second REACTION step
    assert area.steps[3].position == 3
    assert area.steps[3].step_type.value == "reaction"


def test_create_area_with_single_step(db_session: Session):
    """Test creating an area with just one ACTION step."""
    user = User(email="test2@example.com", hashed_password="fake_hash")
    db_session.add(user)
    db_session.commit()

    area_data = AreaCreate(
        name="Single-step Area",
        steps=[
            AreaStepCreate(
                position=0,
                step_type="action",
                service_slug="time",
                action_key="every_interval",
                config={"interval_seconds": 60},
            ),
        ],
    )

    area = create_area(db_session, area_data, str(user.id))

    assert area.id is not None
    assert len(area.steps) == 1
    assert area.steps[0].step_type.value == "action"


def test_create_area_duplicate_name(db_session: Session):
    """Test that creating an area with duplicate name raises error."""
    user = User(email="test3@example.com", hashed_password="fake_hash")
    db_session.add(user)
    db_session.commit()

    area_data = AreaCreate(
        name="Duplicate Area",
        steps=[
            AreaStepCreate(
                position=0,
                step_type="action",
                service_slug="time",
                action_key="every_interval",
                config={},
            ),
        ],
    )

    # Create first area
    create_area(db_session, area_data, str(user.id))

    # Try to create second area with same name
    with pytest.raises(DuplicateAreaError):
        create_area(db_session, area_data, str(user.id))


def test_get_area_by_id(db_session: Session):
    """Test fetching an area by ID."""
    user = User(email="test4@example.com", hashed_password="fake_hash")
    db_session.add(user)
    db_session.commit()

    area_data = AreaCreate(
        name="Test Area",
        steps=[
            AreaStepCreate(
                position=0,
                step_type="action",
                service_slug="time",
                action_key="every_interval",
                config={},
            ),
        ],
    )

    created_area = create_area(db_session, area_data, str(user.id))

    # Fetch by ID
    fetched_area = get_area_by_id(db_session, str(created_area.id))

    assert fetched_area is not None
    assert fetched_area.id == created_area.id
    assert fetched_area.name == "Test Area"
    assert len(fetched_area.steps) == 1


def test_get_areas_by_user(db_session: Session):
    """Test fetching all areas for a user."""
    user = User(email="test5@example.com", hashed_password="fake_hash")
    db_session.add(user)
    db_session.commit()

    # Create multiple areas
    for i in range(3):
        area_data = AreaCreate(
            name=f"Area {i}",
            steps=[
                AreaStepCreate(
                    position=0,
                    step_type="action",
                    service_slug="time",
                    action_key="every_interval",
                    config={},
                ),
            ],
        )
        create_area(db_session, area_data, str(user.id))

    # Fetch all areas for user
    areas = get_areas_by_user(db_session, str(user.id))

    assert len(areas) == 3
    assert all(area.user_id == user.id for area in areas)


def test_update_area_name(db_session: Session):
    """Test updating area name."""
    user = User(email="test6@example.com", hashed_password="fake_hash")
    db_session.add(user)
    db_session.commit()

    area_data = AreaCreate(
        name="Original Name",
        steps=[
            AreaStepCreate(
                position=0,
                step_type="action",
                service_slug="time",
                action_key="every_interval",
                config={},
            ),
        ],
    )

    area = create_area(db_session, area_data, str(user.id))

    # Update name
    update_data = AreaUpdate(name="Updated Name")
    updated_area = update_area(db_session, str(area.id), update_data, user_id=str(user.id))

    assert updated_area.name == "Updated Name"
    assert len(updated_area.steps) == 1  # Steps unchanged


def test_update_area_steps(db_session: Session):
    """Test updating area steps."""
    user = User(email="test7@example.com", hashed_password="fake_hash")
    db_session.add(user)
    db_session.commit()

    # Create area with one step
    area_data = AreaCreate(
        name="Test Area",
        steps=[
            AreaStepCreate(
                position=0,
                step_type="action",
                service_slug="time",
                action_key="every_interval",
                config={},
            ),
        ],
    )

    area = create_area(db_session, area_data, str(user.id))
    assert len(area.steps) == 1

    # Update with new steps
    update_data = AreaUpdate(
        steps=[
            AreaStepCreate(
                position=0,
                step_type="action",
                service_slug="time",
                action_key="every_interval",
                config={"interval_seconds": 300},
            ),
            AreaStepCreate(
                position=1,
                step_type="reaction",
                service_slug="debug",
                action_key="log",
                config={"message": "New reaction"},
            ),
        ]
    )

    updated_area = update_area(db_session, str(area.id), update_data, user_id=str(user.id))

    assert len(updated_area.steps) == 2
    assert updated_area.steps[0].config == {"interval_seconds": 300}
    assert updated_area.steps[1].service_slug == "debug"


def test_update_area_enabled_status(db_session: Session):
    """Test enabling/disabling an area."""
    user = User(email="test8@example.com", hashed_password="fake_hash")
    db_session.add(user)
    db_session.commit()

    area_data = AreaCreate(
        name="Test Area",
        steps=[
            AreaStepCreate(
                position=0,
                step_type="action",
                service_slug="time",
                action_key="every_interval",
                config={},
            ),
        ],
    )

    area = create_area(db_session, area_data, str(user.id))
    assert area.enabled is True

    # Disable
    update_data = AreaUpdate(enabled=False)
    updated_area = update_area(db_session, str(area.id), update_data, user_id=str(user.id))

    assert updated_area.enabled is False


def test_delete_area(db_session: Session):
    """Test deleting an area."""
    user = User(email="test9@example.com", hashed_password="fake_hash")
    db_session.add(user)
    db_session.commit()

    area_data = AreaCreate(
        name="Test Area",
        steps=[
            AreaStepCreate(
                position=0,
                step_type="action",
                service_slug="time",
                action_key="every_interval",
                config={},
            ),
        ],
    )

    area = create_area(db_session, area_data, str(user.id))

    # Delete
    result = delete_area(db_session, str(area.id))
    assert result is True

    # Verify it's gone
    fetched = get_area_by_id(db_session, str(area.id))
    assert fetched is None


def test_delete_area_cascades_to_steps(db_session: Session):
    """Test that deleting an area also deletes its steps."""
    from app.models.area_step import AreaStep

    user = User(email="test10@example.com", hashed_password="fake_hash")
    db_session.add(user)
    db_session.commit()

    area_data = AreaCreate(
        name="Test Area",
        steps=[
            AreaStepCreate(
                position=0,
                step_type="action",
                service_slug="time",
                action_key="every_interval",
                config={},
            ),
            AreaStepCreate(
                position=1,
                step_type="reaction",
                service_slug="debug",
                action_key="log",
                config={},
            ),
        ],
    )

    area = create_area(db_session, area_data, str(user.id))
    area_id = area.id

    # Verify steps exist
    steps = db_session.query(AreaStep).filter(AreaStep.area_id == area_id).all()
    assert len(steps) == 2

    # Delete area
    delete_area(db_session, str(area_id))

    # Verify steps are also deleted
    steps = db_session.query(AreaStep).filter(AreaStep.area_id == area_id).all()
    assert len(steps) == 0
