"""Area API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.dependencies import require_active_user
from app.db.session import get_db
from app.models.user import User
from app.models.area import Area
from app.models.area_step import AreaStep
from app.schemas.area import AreaCreate, AreaUpdate, AreaResponse
from app.schemas.area_step import AreaStepCreate, AreaStepUpdate, AreaStepResponse
from app.services.areas import (
    create_area,
    get_areas_by_user,
    update_area,
    delete_area,
    enable_area,
    disable_area,
    AreaNotFoundError,
    DuplicateAreaError,
)
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
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> AreaResponse:
    """Create a new area for the authenticated user."""
    try:
        area = create_area(db, area_in, str(current_user.id))
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
    )
    
    try:
        area = create_area(db, area_create, str(current_user.id), steps=area_with_steps.steps)
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


@router.patch(
    "/areas/{area_id}",
    response_model=AreaResponse,
    dependencies=[Depends(require_active_user)],
)
def update_user_area(
    area_id: str,
    area_in: AreaUpdate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> AreaResponse:
    """Update an existing area."""
    # Load first and verify ownership BEFORE performing the update
    # This avoids persisting changes for non-owners.
    existing = db.query(Area).filter(Area.id == area_id).first()
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
        updated = update_area(db, area_id, area_in, user_id=str(current_user.id))
        return AreaResponse.model_validate(updated)
    except AreaNotFoundError:
        # In case service layer also checks and signals not found
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
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> bool:
    """Delete an area by its ID."""
    # First, get the area to check ownership
    area = db.query(Area).filter(Area.id == area_id).first()
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
    
    return delete_area(db, area_id)


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
    area = db.query(Area).filter(Area.id == area_id).first()
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
        area = enable_area(db, area_id, user_id=str(current_user.id))
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
    area = db.query(Area).filter(Area.id == area_id).first()
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
        area = disable_area(db, area_id, user_id=str(current_user.id))
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
    area = db.query(Area).filter(Area.id == step_in.area_id).first()
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
    
    try:
        step = create_area_step(db, step_in.area_id, step_in)
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
    area = db.query(Area).filter(Area.id == area_id).first()
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
    
    steps = get_steps_by_area(db, area_id)
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
            detail="You don't have permission to update this step",
        )
    
    try:
        updated_step = update_area_step(db, step_id, step_in)
        return AreaStepResponse.model_validate(updated_step)
    except AreaStepNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Step not found",
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
            detail="You don't have permission to delete this step",
        )
    
    return delete_area_step(db, step_id)


__all__ = ["router"]