"""Repository helpers for interacting with area records."""

from __future__ import annotations

import uuid
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.area import Area
from app.models.area_step import AreaStep
from app.schemas.area import AreaCreate, AreaUpdate
from app.schemas.area_step import AreaStepCreate


def _is_duplicate_area_constraint_violation(exc: IntegrityError) -> bool:
    """Check if the IntegrityError is due to duplicate area constraint violation."""
    error_str = str(exc.orig) if exc.orig else str(exc)
    # Check for the unique constraint on user_id and name
    # This can vary between database backends, so check for multiple patterns
    return "uq_areas_user_id_name" in error_str or (
        "UNIQUE constraint failed" in error_str
        and "user_id" in error_str
        and "name" in error_str
    )


class AreaNotFoundError(Exception):
    """Raised when attempting to access an area that doesn't exist."""

    def __init__(self, area_id: str) -> None:
        super().__init__(f"Area with id '{area_id}' not found")
        self.area_id = area_id


class DuplicateAreaError(Exception):
    """Raised when attempting to create an area that already exists for the user."""

    def __init__(self, user_id: str, name: str) -> None:
        super().__init__(
            f"An area with name '{name}' already exists for user '{user_id}'"
        )
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


def create_area(
    db: Session,
    area_in: AreaCreate,
    user_id: str,
    steps: Optional[List[AreaStepCreate]] = None,
) -> Area:
    """Create a new area with optional steps."""
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
        db.flush()  # Flush to get area.id without committing yet

        # Create steps if provided (in same transaction)
        if steps:
            # First pass: create all steps and build ID mapping
            created_steps: List[AreaStep] = []
            old_id_to_new_id = {}  # Map from old client-side IDs to new UUIDs

            for step_in in steps:
                step = AreaStep(
                    area_id=area.id,
                    step_type=step_in.step_type,
                    order=step_in.order,
                    service=step_in.service,
                    action=step_in.action,
                    config=step_in.config,
                )
                db.add(step)
                created_steps.append(step)

            # Flush to assign UUIDs to all steps
            db.flush()

            # Build mapping: if step config has a 'clientId' field (client-side temp ID), map it to the new UUID
            # Otherwise, map by order index
            for i, step in enumerate(created_steps):
                # Check if the original step_in had a clientId in its config
                if steps[i].config and "clientId" in steps[i].config:
                    old_id = steps[i].config["clientId"]
                    old_id_to_new_id[str(old_id)] = str(step.id)
                # Also map by order for robustness
                old_id_to_new_id[f"order_{i}"] = str(step.id)

            # Second pass: update all 'targets' arrays in configs to use new UUIDs
            for step in created_steps:
                if (
                    step.config
                    and "targets" in step.config
                    and isinstance(step.config["targets"], list)
                ):
                    updated_targets = []
                    for target_id in step.config["targets"]:
                        # Try to find the new UUID for this target
                        new_target_id = old_id_to_new_id.get(str(target_id))
                        if new_target_id is None:
                            raise ValueError(
                                f"Invalid target ID '{target_id}' in step connections"
                            )
                        updated_targets.append(new_target_id)

                    # Update the step's config with the new targets
                    step.config = {**step.config, "targets": updated_targets}

        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _is_duplicate_area_constraint_violation(exc):
            raise DuplicateAreaError(user_id, area_in.name) from exc
        raise

    db.refresh(area)
    return area


def update_area(
    db: Session, area_id: str, area_in: AreaUpdate, *, user_id: Optional[str] = None
) -> Area:
    """Update an existing area.

    If user_id is provided, scope the lookup to that user to prevent cross-user updates.
    """
    uuid_area_id = uuid.UUID(area_id)
    if user_id is not None:
        uuid_user_id = uuid.UUID(user_id)
        statement = select(Area).where(
            Area.id == uuid_area_id, Area.user_id == uuid_user_id
        )
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


def update_area_with_steps(
    db: Session,
    area_id: str,
    area_in: AreaUpdate,
    steps: List[AreaStepCreate],
    *,
    user_id: Optional[str] = None,
) -> Area:
    """Update an existing area and replace all its steps.

    This will delete all existing steps and create new ones from the provided list.
    """
    # First update the area metadata
    area = update_area(db, area_id, area_in, user_id=user_id)

    # Delete all existing steps for this area
    uuid_area_id = uuid.UUID(area_id)
    db.query(AreaStep).filter(AreaStep.area_id == uuid_area_id).delete()

    # Create new steps with ID remapping
    created_steps: List[AreaStep] = []
    old_id_to_new_id = {}  # Map from old client-side IDs to new UUIDs

    for step_in in steps:
        step = AreaStep(
            area_id=uuid_area_id,
            step_type=step_in.step_type,
            order=step_in.order,
            service=step_in.service,
            action=step_in.action,
            config=step_in.config,
        )
        db.add(step)
        created_steps.append(step)

    # Flush to assign UUIDs to all steps
    db.flush()

    # Build mapping from old IDs to new UUIDs
    for i, step in enumerate(created_steps):
        # Check if the original step_in had a clientId in its config
        if steps[i].config and "clientId" in steps[i].config:
            old_id = steps[i].config["clientId"]
            old_id_to_new_id[str(old_id)] = str(step.id)
        # Also map by order for robustness
        old_id_to_new_id[f"order_{i}"] = str(step.id)

    # Update all 'targets' arrays in configs to use new UUIDs
    for step in created_steps:
        if (
            step.config
            and "targets" in step.config
            and isinstance(step.config["targets"], list)
        ):
            updated_targets = []
            for target_id in step.config["targets"]:
                # Try to find the new UUID for this target
                new_target_id = old_id_to_new_id.get(str(target_id))
                if new_target_id is None:
                    raise ValueError(
                        f"Invalid target ID '{target_id}' in step connections"
                    )
                updated_targets.append(new_target_id)

            # Update the step's config with the new targets
            step.config = {**step.config, "targets": updated_targets}

    db.commit()
    db.refresh(area)
    return area


__all__ = [
    "AreaNotFoundError",
    "DuplicateAreaError",
    "create_area",
    "get_area_by_id",
    "get_areas_by_user",
    "update_area",
    "update_area_with_steps",
    "delete_area",
    "enable_area",
    "disable_area",
]
