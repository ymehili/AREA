"""Repository helpers for interacting with area step records."""

from __future__ import annotations

import uuid as uuid_module
from typing import List, Union
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.area_step import AreaStep
from app.schemas.area_step import AreaStepCreate, AreaStepUpdate


def _ensure_uuid(value: Union[str, uuid_module.UUID]) -> uuid_module.UUID:
    """Convert string to UUID if needed."""
    if isinstance(value, str):
        return uuid_module.UUID(value)
    return value


class AreaStepNotFoundError(Exception):
    """Raised when attempting to access an area step that doesn't exist."""

    def __init__(self, step_id: str) -> None:
        super().__init__(f"AreaStep with id '{step_id}' not found")
        self.step_id = step_id


class DuplicateStepOrderError(Exception):
    """Raised when attempting to create a step with duplicate order in same area."""

    def __init__(self, area_id: str, order: int) -> None:
        super().__init__(
            f"A step with order {order} already exists for area '{area_id}'"
        )
        self.area_id = area_id
        self.order = order


def create_area_step(db: Session, area_id: Union[str, uuid_module.UUID], step_in: AreaStepCreate) -> AreaStep:
    """Create a new area step."""
    step = AreaStep(
        area_id=_ensure_uuid(area_id),
        step_type=step_in.step_type,
        order=step_in.order,
        service=step_in.service,
        action=step_in.action,
        config=step_in.config,
    )

    db.add(step)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateStepOrderError(area_id, step_in.order) from exc

    db.refresh(step)
    return step


def get_steps_by_area(db: Session, area_id: Union[str, uuid_module.UUID]) -> List[AreaStep]:
    """Fetch all steps for a specific area, ordered by execution order."""
    area_id = _ensure_uuid(area_id)
    statement = select(AreaStep).where(AreaStep.area_id == area_id).order_by(AreaStep.order)
    result = db.execute(statement)
    return list(result.scalars().all())


def get_area_step_by_id(db: Session, step_id: Union[str, uuid_module.UUID]) -> AreaStep | None:
    """Fetch an area step by its ID."""
    step_id = _ensure_uuid(step_id)
    statement = select(AreaStep).where(AreaStep.id == step_id)
    result = db.execute(statement)
    return result.scalar_one_or_none()


def update_area_step(db: Session, step_id: Union[str, uuid_module.UUID], step_in: AreaStepUpdate) -> AreaStep:
    """Update an existing area step."""
    step = get_area_step_by_id(db, step_id)
    if step is None:
        raise AreaStepNotFoundError(step_id)

    # Update fields if provided
    if step_in.step_type is not None:
        step.step_type = step_in.step_type

    if step_in.order is not None:
        step.order = step_in.order

    if step_in.service is not None:
        step.service = step_in.service

    if step_in.action is not None:
        step.action = step_in.action

    if step_in.config is not None:
        step.config = step_in.config

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateStepOrderError(str(step.area_id), step.order) from exc

    db.refresh(step)
    return step


def delete_area_step(db: Session, step_id: Union[str, uuid_module.UUID]) -> bool:
    """Delete an area step by its ID."""
    step = get_area_step_by_id(db, step_id)
    if step is None:
        return False

    db.delete(step)
    db.commit()
    return True


def reorder_area_steps(db: Session, area_id: Union[str, uuid_module.UUID], step_order: List[Union[str, uuid_module.UUID]]) -> List[AreaStep]:
    """Reorder area steps by providing a list of step IDs in desired order.

    Args:
        db: Database session
        area_id: ID of the area whose steps are being reordered
        step_order: List of step IDs in the desired order

    Returns:
        List of reordered AreaStep objects

    Raises:
        AreaStepNotFoundError: If any step_id doesn't exist or doesn't belong to the area
    """
    area_id = _ensure_uuid(area_id)

    # Fetch all steps by the provided IDs
    steps = []
    for step_id in step_order:
        step = get_area_step_by_id(db, step_id)
        if step is None:
            raise AreaStepNotFoundError(str(step_id))
        # Validate that step belongs to the specified area
        if step.area_id != area_id:
            raise AreaStepNotFoundError(str(step_id))
        steps.append(step)

    # Update order for each step using two-phase approach to avoid unique constraint violations
    # Phase 1: Set all steps to temporary negative order values
    for i, step in enumerate(steps):
        step.order = -(i + 1)

    db.flush()  # Flush phase 1 changes

    # Phase 2: Set final order values
    for new_order, step in enumerate(steps):
        step.order = new_order

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise exc

    # Refresh all steps and return
    for step in steps:
        db.refresh(step)

    return steps


__all__ = [
    "AreaStepNotFoundError",
    "DuplicateStepOrderError",
    "create_area_step",
    "get_steps_by_area",
    "get_area_step_by_id",
    "update_area_step",
    "delete_area_step",
    "reorder_area_steps",
]
