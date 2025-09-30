"""Repository helpers for interacting with area records."""

from __future__ import annotations

import uuid
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.area import Area
from app.schemas.area import AreaCreate, AreaUpdate


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
    """Fetch an area by its ID."""
    uuid_area_id = uuid.UUID(area_id)
    statement = select(Area).where(Area.id == uuid_area_id)
    result = db.execute(statement)
    return result.scalar_one_or_none()


def get_areas_by_user(db: Session, user_id: str) -> List[Area]:
    """Fetch all areas for a specific user."""
    uuid_user_id = uuid.UUID(user_id)
    statement = select(Area).where(Area.user_id == uuid_user_id)
    result = db.execute(statement)
    return list(result.scalars().all())


def create_area(db: Session, area_in: AreaCreate, user_id: str) -> Area:
    """Create a new area."""
    uuid_user_id = uuid.UUID(user_id)
    area = Area(
        user_id=uuid_user_id,
        name=area_in.name,
        trigger_service=area_in.trigger_service,
        trigger_action=area_in.trigger_action,
        trigger_params=area_in.trigger_params,
        reaction_service=area_in.reaction_service,
        reaction_action=area_in.reaction_action,
        reaction_params=area_in.reaction_params,
    )

    db.add(area)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateAreaError(user_id, area_in.name) from exc

    db.refresh(area)
    return area


def update_area(db: Session, area_id: str, area_in: AreaUpdate, *, user_id: Optional[str] = None) -> Area:
    """Update an existing area.

    If user_id is provided, scope the lookup to that user to prevent cross-user updates.
    """
    uuid_area_id = uuid.UUID(area_id)
    if user_id is not None:
        uuid_user_id = uuid.UUID(user_id)
        statement = select(Area).where(Area.id == uuid_area_id, Area.user_id == uuid_user_id)
        result = db.execute(statement)
        area = result.scalar_one_or_none()
    else:
        area = get_area_by_id(db, area_id)
    if area is None:
        raise AreaNotFoundError(area_id)

    # Update fields if provided
    if area_in.name is not None:
        area.name = area_in.name

    if area_in.trigger_service is not None:
        area.trigger_service = area_in.trigger_service

    if area_in.trigger_action is not None:
        area.trigger_action = area_in.trigger_action

    if area_in.trigger_params is not None:
        area.trigger_params = area_in.trigger_params

    if area_in.reaction_service is not None:
        area.reaction_service = area_in.reaction_service

    if area_in.reaction_action is not None:
        area.reaction_action = area_in.reaction_action

    if area_in.reaction_params is not None:
        area.reaction_params = area_in.reaction_params

    if area_in.enabled is not None:
        area.enabled = area_in.enabled

    db.commit()
    db.refresh(area)
    return area


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