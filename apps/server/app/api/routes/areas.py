"""Area API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api.dependencies import require_active_user
from app.db.session import get_db
from app.models.user import User
from app.models.area import Area
from app.schemas.area import AreaCreate, AreaUpdate, AreaResponse
from app.services.areas import (
    create_area,
    get_areas_by_user,
    update_area,
    delete_area,
    enable_area,
    disable_area,
    AreaNotFoundError,
)

router = APIRouter(tags=["areas"])


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
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
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
        updated = update_area(db, area_id, area_in)
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
        area = enable_area(db, area_id)
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
        area = disable_area(db, area_id)
        return AreaResponse.model_validate(area)
    except AreaNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Area not found",
        )


__all__ = ["router"]