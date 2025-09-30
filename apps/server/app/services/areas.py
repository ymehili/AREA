"""Repository helpers for interacting with area records."""

from __future__ import annotations

import uuid
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError

from app.models.area import Area
from app.models.area_step import AreaStep, AreaStepType
from app.schemas.area import AreaCreate, AreaUpdate, AreaStepCreate


class AreaNotFoundError(Exception):
    """Raised when attempting to access an area that doesn't exist."""

    def __init__(self, area_id: str) -> None:
        super().__init__(f"Area with id '{area_id}' not found")
        self.area_id = area_id


class DuplicateAreaError(Exception):
    """Raised when attempting to create an area that already exists for the user."""

    def __init__(self, user_id: str, name: str) -> None:
        super().__init__(f"An area with name '{name}' already exists for user '{user_id}'")
        self.user_id = user_id
        self.name = name


def get_area_by_id(db: Session, area_id: str) -> Optional[Area]:
    """Fetch an area by its ID with steps eagerly loaded."""
    uuid_area_id = uuid.UUID(area_id)
    statement = select(Area).where(Area.id == uuid_area_id).options(selectinload(Area.steps))
    result = db.execute(statement)
    return result.scalar_one_or_none()


def get_areas_by_user(db: Session, user_id: str) -> List[Area]:
    """Fetch all areas for a specific user with steps eagerly loaded."""
    uuid_user_id = uuid.UUID(user_id)
    statement = select(Area).where(Area.user_id == uuid_user_id).options(selectinload(Area.steps))
    result = db.execute(statement)
    return list(result.scalars().all())


def _create_area_steps(area: Area, steps_data: list[AreaStepCreate]) -> list[AreaStep]:
    """Helper to create AreaStep instances from schema data."""
    steps = []
    for step_data in steps_data:
        step = AreaStep(
            area_id=area.id,
            position=step_data.position,
            step_type=AreaStepType(step_data.step_type),
            service_slug=step_data.service_slug,
            action_key=step_data.action_key,
            config=step_data.config,
        )
        steps.append(step)
    return steps


def create_area(db: Session, area_in: AreaCreate, user_id: str) -> Area:
    """Create a new area with multi-step workflow."""
    uuid_user_id = uuid.UUID(user_id)

    # Validate that we have at least one ACTION step (schema already does this, but double-check)
    if not area_in.steps or area_in.steps[0].step_type != "action":
        raise ValueError("Area must have at least one step, and the first step must be an ACTION")

    try:
        # Create the area
        area = Area(
            user_id=uuid_user_id,
            name=area_in.name,
        )
        db.add(area)
        db.flush()  # Get the area.id for foreign key references

        # Create and attach steps
        steps = _create_area_steps(area, area_in.steps)
        for step in steps:
            db.add(step)

        db.commit()
        db.refresh(area, attribute_names=["steps"])
        return area

    except IntegrityError as exc:
        db.rollback()
        raise DuplicateAreaError(user_id, area_in.name) from exc
    except Exception:
        db.rollback()
        raise


def update_area(db: Session, area_id: str, area_in: AreaUpdate, *, user_id: Optional[str] = None) -> Area:
    """Update an existing area.

    If user_id is provided, scope the lookup to that user to prevent cross-user updates.
    If steps are provided in the update, the existing steps will be replaced entirely.
    """
    uuid_area_id = uuid.UUID(area_id)
    if user_id is not None:
        uuid_user_id = uuid.UUID(user_id)
        statement = (
            select(Area)
            .where(Area.id == uuid_area_id, Area.user_id == uuid_user_id)
            .options(selectinload(Area.steps))
        )
        result = db.execute(statement)
        area = result.scalar_one_or_none()
    else:
        area = get_area_by_id(db, area_id)

    if area is None:
        raise AreaNotFoundError(area_id)

    try:
        # Update name if provided
        if area_in.name is not None:
            area.name = area_in.name

        # Update enabled status if provided
        if area_in.enabled is not None:
            area.enabled = area_in.enabled

        # Replace steps if provided
        if area_in.steps is not None:
            # Validate that we have at least one ACTION step
            if not area_in.steps or area_in.steps[0].step_type != "action":
                raise ValueError("Area must have at least one step, and the first step must be an ACTION")

            # Delete existing steps (cascade will handle this, but explicit is clearer)
            for step in area.steps:
                db.delete(step)

            # Create new steps
            new_steps = _create_area_steps(area, area_in.steps)
            for step in new_steps:
                db.add(step)

        db.commit()
        db.refresh(area, attribute_names=["steps"])
        return area

    except IntegrityError as exc:
        db.rollback()
        if "uq_areas_user_id_name" in str(exc):
            raise DuplicateAreaError(str(area.user_id), area_in.name or area.name) from exc
        raise
    except Exception:
        db.rollback()
        raise


def delete_area(db: Session, area_id: str) -> bool:
    """Delete an area by its ID."""
    area = get_area_by_id(db, area_id)
    if area is None:
        return False

    db.delete(area)
    db.commit()
    return True


def enable_area(db: Session, area_id: str, *, user_id: Optional[str] = None) -> Area:
    """Enable an area."""
    return update_area(db, area_id, AreaUpdate(enabled=True), user_id=user_id)


def disable_area(db: Session, area_id: str, *, user_id: Optional[str] = None) -> Area:
    """Disable an area."""
    return update_area(db, area_id, AreaUpdate(enabled=False), user_id=user_id)


__all__ = [
    "AreaNotFoundError",
    "DuplicateAreaError",
    "create_area",
    "get_area_by_id",
    "get_areas_by_user",
    "update_area",
    "delete_area",
    "enable_area",
    "disable_area",
]