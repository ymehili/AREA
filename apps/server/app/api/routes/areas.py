"""Area API routes."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.background import BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.dependencies import require_active_user
from app.db.session import get_db
from app.models.user import User
from app.models.area import Area
from app.schemas.area import AreaCreate, AreaUpdate, AreaResponse
from app.schemas.area_step import AreaStepCreate, AreaStepUpdate, AreaStepResponse
from app.services.areas import (
    create_area,
    get_areas_by_user,
    update_area,
    update_area_with_steps,
    delete_area,
    enable_area,
    disable_area,
    AreaNotFoundError,
    DuplicateAreaError,
)
from app.services.user_activity_logs import log_user_activity_task
from app.services.area_steps import (
    create_area_step,
    get_steps_by_area,
    get_area_step_by_id,
    update_area_step,
    delete_area_step,
    AreaStepNotFoundError,
    DuplicateStepOrderError,
)

router = APIRouter(tags=["areas"])


from pydantic import BaseModel
from typing import List as TypingList


class AreaCreateWithSteps(BaseModel):
    """Schema for creating an area with steps."""

    name: str
    trigger_service: str
    trigger_action: str
    reaction_service: str
    reaction_action: str
    trigger_params: Optional[dict] = None
    reaction_params: Optional[dict] = None
    description: Optional[str] = None
    is_active: Optional[bool] = True
    steps: TypingList[AreaStepCreate]


@router.post(
    "/areas",
    response_model=AreaResponse,
    dependencies=[Depends(require_active_user)],
)
def create_user_area(
    area_in: AreaCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> AreaResponse:
    """Create a new area for the authenticated user."""
    try:
        area = create_area(db, area_in, str(current_user.id))

        # Schedule area creation activity log using background task
        # so that if logging fails, the main operation is still successful
        background_tasks.add_task(
            log_user_activity_task,
            user_id=str(current_user.id),
            action_type="area_created",
            details=f"User created new area: {area.name}",
            service_name=f"{area.trigger_service} → {area.reaction_service}",
            status="success",
        )

        return AreaResponse.model_validate(area)
    except DuplicateAreaError:
        raise HTTPException(
            status_code=409,
            detail="An area with this name already exists for your account.",
        )


@router.post(
    "/areas/with-steps",
    response_model=AreaResponse,
    dependencies=[Depends(require_active_user)],
)
def create_user_area_with_steps(
    area_with_steps: AreaCreateWithSteps,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> AreaResponse:
    """Create a new area with steps for the authenticated user."""
    # Convert AreaCreateWithSteps to AreaCreate
    area_create = AreaCreate(
        name=area_with_steps.name,
        trigger_service=area_with_steps.trigger_service,
        trigger_action=area_with_steps.trigger_action,
        reaction_service=area_with_steps.reaction_service,
        reaction_action=area_with_steps.reaction_action,
        trigger_params=area_with_steps.trigger_params,
        reaction_params=area_with_steps.reaction_params,
    )

    # Remove area_id from steps if present (it's not needed for internal creation)
    # Area ID will be set by the create_area service when the area is created
    processed_steps = []
    for step in area_with_steps.steps:
        # Create step schema, excluding area_id (will be set by create_area service)
        step_dict = step.model_dump(exclude={"area_id"})
        processed_step = AreaStepCreate(**step_dict)
        processed_steps.append(processed_step)

    try:
        area = create_area(db, area_create, str(current_user.id), steps=processed_steps)

        # Schedule area creation activity log using background task
        # so that if logging fails, the main operation is still successful
        background_tasks.add_task(
            log_user_activity_task,
            user_id=str(current_user.id),
            action_type="area_created",
            details=f"User created new area: {area.name}",
            service_name=f"{area.trigger_service} → {area.reaction_service}",
            status="success",
        )

        return AreaResponse.model_validate(area)
    except DuplicateAreaError:
        raise HTTPException(
            status_code=409,
            detail="An area with this name already exists for your account.",
        )


@router.get(
    "/areas",
    response_model=List[AreaResponse],
    dependencies=[Depends(require_active_user)],
)
def list_user_areas(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> List[AreaResponse]:
    """List all areas created by the authenticated user."""
    areas = get_areas_by_user(db, str(current_user.id))
    return [AreaResponse.model_validate(area) for area in areas]


@router.get(
    "/areas/{area_id}",
    response_model=AreaResponse,
    dependencies=[Depends(require_active_user)],
)
def get_area_by_id_endpoint(
    area_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> AreaResponse:
    """Get a specific area by its ID with its steps."""
    import uuid

    uuid_area_id = uuid.UUID(area_id)
    # Query the area with the UUID object
    area = db.query(Area).filter(Area.id == uuid_area_id).first()
    if not area:
        raise HTTPException(
            status_code=404,
            detail="Area not found",
        )

    # Check if the area belongs to the current user
    if str(area.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this area",
        )

    # Load steps for this area
    steps = get_steps_by_area(db, str(uuid_area_id))

    # Convert to response format with steps
    area_dict = {
        "id": area.id,
        "user_id": area.user_id,
        "name": area.name,
        "trigger_service": area.trigger_service,
        "trigger_action": area.trigger_action,
        "trigger_params": area.trigger_params,
        "reaction_service": area.reaction_service,
        "reaction_action": area.reaction_action,
        "reaction_params": area.reaction_params,
        "enabled": area.enabled,
        "created_at": area.created_at,
        "updated_at": area.updated_at,
        "steps": [AreaStepResponse.model_validate(step) for step in steps],
    }

    return AreaResponse.model_validate(area_dict)


@router.patch(
    "/areas/{area_id}",
    response_model=AreaResponse,
    dependencies=[Depends(require_active_user)],
)
def update_user_area(
    area_id: str,
    area_in: AreaUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> AreaResponse:
    """Update an existing area."""
    # Load first and verify ownership BEFORE performing the update
    # This avoids persisting changes for non-owners.
    import uuid

    uuid_area_id = uuid.UUID(area_id)
    existing = db.query(Area).filter(Area.id == uuid_area_id).first()
    if not existing:
        raise HTTPException(
            status_code=404,
            detail="Area not found",
        )
    if str(existing.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to update this area",
        )
    try:
        updated = update_area(
            db, str(uuid_area_id), area_in, user_id=str(current_user.id)
        )

        # Schedule area update activity log using background task
        # so that if logging fails, the main operation is still successful
        background_tasks.add_task(
            log_user_activity_task,
            user_id=str(current_user.id),
            action_type="area_updated",
            details=f"User updated area: {updated.name}",
            service_name=f"{updated.trigger_service} → {updated.reaction_service}",
            status="success",
        )

        return AreaResponse.model_validate(updated)
    except AreaNotFoundError:
        # In case service layer also checks and signals not found
        raise HTTPException(
            status_code=404,
            detail="Area not found",
        )


@router.put(
    "/areas/{area_id}/with-steps",
    response_model=AreaResponse,
    dependencies=[Depends(require_active_user)],
)
def update_user_area_with_steps(
    area_id: str,
    area_with_steps: AreaCreateWithSteps,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> AreaResponse:
    """Update an existing area with steps."""
    # Verify ownership first
    import uuid

    uuid_area_id = uuid.UUID(area_id)
    existing = db.query(Area).filter(Area.id == uuid_area_id).first()
    if not existing:
        raise HTTPException(
            status_code=404,
            detail="Area not found",
        )
    if str(existing.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to update this area",
        )

    # Convert to AreaUpdate
    area_update = AreaUpdate(
        name=area_with_steps.name,
        trigger_service=area_with_steps.trigger_service,
        trigger_action=area_with_steps.trigger_action,
        reaction_service=area_with_steps.reaction_service,
        reaction_action=area_with_steps.reaction_action,
        enabled=area_with_steps.is_active,
    )

    # Remove area_id from steps if present (it's not needed for internal processing)
    processed_steps = []
    for step in area_with_steps.steps:
        # Create step schema, excluding area_id (will be set by update service)
        step_dict = step.model_dump(exclude={"area_id"})
        processed_step = AreaStepCreate(**step_dict)
        processed_steps.append(processed_step)

    try:
        area = update_area_with_steps(
            db,
            str(uuid_area_id),
            area_update,
            processed_steps,
            user_id=str(current_user.id),
        )

        # Schedule area update activity log using background task
        # so that if logging fails, the main operation is still successful
        background_tasks.add_task(
            log_user_activity_task,
            user_id=str(current_user.id),
            action_type="area_updated",
            details=f"User updated area: {area.name}",
            service_name=f"{area.trigger_service} → {area.reaction_service}",
            status="success",
        )

        # Load the steps for the response
        steps = get_steps_by_area(db, str(uuid_area_id))
        area_dict = {
            "id": area.id,
            "user_id": area.user_id,
            "name": area.name,
            "trigger_service": area.trigger_service,
            "trigger_action": area.trigger_action,
            "trigger_params": area.trigger_params,
            "reaction_service": area.reaction_service,
            "reaction_action": area.reaction_action,
            "reaction_params": area.reaction_params,
            "enabled": area.enabled,
            "created_at": area.created_at,
            "updated_at": area.updated_at,
            "steps": [AreaStepResponse.model_validate(step) for step in steps],
        }
        return AreaResponse.model_validate(area_dict)
    except AreaNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Area not found",
        )


@router.delete(
    "/areas/{area_id}",
    response_model=bool,
    dependencies=[Depends(require_active_user)],
)
def delete_user_area(
    area_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> bool:
    """Delete an area by its ID."""
    # First, get the area to check ownership
    import uuid

    uuid_area_id = uuid.UUID(area_id)
    area = db.query(Area).filter(Area.id == uuid_area_id).first()
    if not area:
        raise HTTPException(
            status_code=404,
            detail="Area not found",
        )

    # Check if the area belongs to the current user
    if str(area.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this area",
        )

    # Schedule area deletion activity log using background task
    # so that if logging fails, the main operation is still successful
    background_tasks.add_task(
        log_user_activity_task,
        user_id=str(current_user.id),
        action_type="area_deleted",
        details=f"User deleted area: {area.name}",
        service_name=f"{area.trigger_service} → {area.reaction_service}",
        status="success",
    )

    return delete_area(db, str(uuid_area_id))


@router.post(
    "/areas/{area_id}/enable",
    response_model=AreaResponse,
    dependencies=[Depends(require_active_user)],
)
def enable_user_area(
    area_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> AreaResponse:
    """Enable an area."""
    # First, get the area to check ownership
    import uuid

    uuid_area_id = uuid.UUID(area_id)
    area = db.query(Area).filter(Area.id == uuid_area_id).first()
    if not area:
        raise HTTPException(
            status_code=404,
            detail="Area not found",
        )

    # Check if the area belongs to the current user
    if str(area.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to enable this area",
        )

    try:
        area = enable_area(db, str(uuid_area_id), user_id=str(current_user.id))
        return AreaResponse.model_validate(area)
    except AreaNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Area not found",
        )


@router.post(
    "/areas/{area_id}/disable",
    response_model=AreaResponse,
    dependencies=[Depends(require_active_user)],
)
def disable_user_area(
    area_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> AreaResponse:
    """Disable an area."""
    # First, get the area to check ownership
    import uuid

    uuid_area_id = uuid.UUID(area_id)
    area = db.query(Area).filter(Area.id == uuid_area_id).first()
    if not area:
        raise HTTPException(
            status_code=404,
            detail="Area not found",
        )

    # Check if the area belongs to the current user
    if str(area.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to disable this area",
        )

    try:
        area = disable_area(db, str(uuid_area_id), user_id=str(current_user.id))
        return AreaResponse.model_validate(area)
    except AreaNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Area not found",
        )


# Area Step API routes
@router.post(
    "/areas/steps",
    response_model=AreaStepResponse,
    dependencies=[Depends(require_active_user)],
)
def create_area_step_endpoint(
    step_in: AreaStepCreate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> AreaStepResponse:
    """Create a new area step for an area."""
    # First, verify the area exists and belongs to the user
    import uuid

    uuid_area_id = uuid.UUID(step_in.area_id)
    area = db.query(Area).filter(Area.id == uuid_area_id).first()
    if not area:
        raise HTTPException(
            status_code=404,
            detail="Area not found",
        )

    # Check if the area belongs to the current user
    if str(area.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to add steps to this area",
        )

    # Create step schema, excluding area_id (will be set by create_area_step service)
    step_dict = step_in.model_dump(exclude={"area_id"})
    step_internal = AreaStepCreate(**step_dict)

    try:
        step = create_area_step(db, str(uuid_area_id), step_internal)
        return AreaStepResponse.model_validate(step)
    except DuplicateStepOrderError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )


@router.get(
    "/areas/{area_id}/steps",
    response_model=List[AreaStepResponse],
    dependencies=[Depends(require_active_user)],
)
def get_area_steps_endpoint(
    area_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> List[AreaStepResponse]:
    """Get all steps for a specific area."""
    # First, verify the area exists and belongs to the user
    import uuid

    uuid_area_id = uuid.UUID(area_id)
    area = db.query(Area).filter(Area.id == uuid_area_id).first()
    if not area:
        raise HTTPException(
            status_code=404,
            detail="Area not found",
        )

    # Check if the area belongs to the current user
    if str(area.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to view steps for this area",
        )

    steps = get_steps_by_area(db, str(uuid_area_id))
    return [AreaStepResponse.model_validate(step) for step in steps]


@router.get(
    "/areas/steps/{step_id}",
    response_model=AreaStepResponse,
    dependencies=[Depends(require_active_user)],
)
def get_area_step_by_id_endpoint(
    step_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> AreaStepResponse:
    """Get a specific area step by its ID."""
    step = get_area_step_by_id(db, step_id)
    if not step:
        raise HTTPException(
            status_code=404,
            detail="Step not found",
        )

    # Check if the step's area belongs to the current user
    area = db.query(Area).filter(Area.id == step.area_id).first()
    if not area or str(area.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this step",
        )

    return AreaStepResponse.model_validate(step)


@router.patch(
    "/areas/steps/{step_id}",
    response_model=AreaStepResponse,
    dependencies=[Depends(require_active_user)],
)
def update_area_step_endpoint(
    step_id: str,
    step_in: AreaStepUpdate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> AreaStepResponse:
    """Update an existing area step."""
    try:
        updated_step = update_area_step(
            db, step_id, step_in, user_id=str(current_user.id)
        )
        return AreaStepResponse.model_validate(updated_step)
    except ValueError as e:
        # Handle invalid UUID format (e.g., temporary client-side IDs like "action-1234567")
        if "badly formed hexadecimal UUID string" in str(e) or "UUID" in str(e):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid step ID format: '{step_id}'. Step must be saved before it can be updated. Please save the area first to generate a valid step ID.",
            )
        raise
    except AreaStepNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Step not found or you don't have permission to update this step",
        )
    except DuplicateStepOrderError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )


@router.delete(
    "/areas/steps/{step_id}",
    response_model=bool,
    dependencies=[Depends(require_active_user)],
)
def delete_area_step_endpoint(
    step_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> bool:
    """Delete an area step."""
    try:
        result = delete_area_step(db, step_id, user_id=str(current_user.id))
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Step not found or you don't have permission to delete this step",
            )
        return result
    except Exception:
        raise HTTPException(
            status_code=404,
            detail="Step not found or you don't have permission to delete this step",
        )


__all__ = ["router"]
