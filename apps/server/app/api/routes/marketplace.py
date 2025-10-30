"""Marketplace API routes."""

from __future__ import annotations

import uuid
from typing import Annotated, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi_pagination import Page, Params
from sqlalchemy.orm import Session

from app.api.dependencies import require_active_user, require_admin_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.marketplace import (
    TemplateCategoryResponse,
    TemplateCloneRequest,
    TemplateCloneResponse,
    TemplatePublishRequest,
    TemplateResponse,
    TemplateTagResponse,
)
from app.services.marketplace import (
    AreaNotFoundError,
    TemplateAlreadyPublishedError,
    TemplateNotApprovedError,
    TemplateNotFoundError,
    UnauthorizedError,
    approve_template,
    clone_template,
    get_template_by_id,
    list_categories,
    list_tags,
    publish_template,
    reject_template,
    search_templates,
)
from app.services.user_activity_logs import log_user_activity_task

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


# ============================================================================
# PUBLIC ENDPOINTS (No authentication required)
# ============================================================================


@router.get("/templates", response_model=Page[TemplateResponse])
async def list_marketplace_templates(
    db: Annotated[Session, Depends(get_db)],
    q: str = Query(None, max_length=100, description="Search query"),
    category: str = Query(None, description="Filter by category"),
    tags: List[str] = Query(default=[], description="Filter by tags"),
    min_rating: float = Query(None, ge=0, le=5, description="Minimum rating"),
    sort_by: str = Query(
        "usage_count",
        pattern="^(created_at|usage_count|rating_average|title)$",
        description="Sort field",
    ),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    params: Params = Depends(),
) -> Page[TemplateResponse]:
    """
    List and search marketplace templates (PUBLIC).
    
    No authentication required. Only returns approved and public templates.
    Supports:
    - Full-text search (q parameter)
    - Category filtering
    - Tag filtering (multiple tags = AND logic)
    - Rating filtering
    - Sorting by usage_count, created_at, rating_average, title
    - Pagination
    """
    # Calculate offset from pagination params
    offset = (params.page - 1) * params.size
    
    templates, total = search_templates(
        db=db,
        query=q,
        category=category,
        tags=tags if tags else None,
        min_rating=min_rating,
        sort_by=sort_by,
        order=order,
        offset=offset,
        limit=params.size,
    )
    
    # Convert to response models
    template_responses = [TemplateResponse.model_validate(t) for t in templates]
    
    # Return paginated response using Page.create
    return Page.create(template_responses, params, total=total)


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template_detail(
    template_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> TemplateResponse:
    """
    Get template details by ID (PUBLIC).
    
    No authentication required for viewing approved templates.
    """
    template = get_template_by_id(db, template_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with id '{template_id}' not found",
        )
    
    # Only return approved and public templates to unauthenticated users
    if template.status != "approved" or template.visibility != "public":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with id '{template_id}' not found",
        )
    
    return TemplateResponse.model_validate(template)


@router.get("/categories", response_model=List[TemplateCategoryResponse])
async def get_template_categories(
    db: Annotated[Session, Depends(get_db)],
) -> List[TemplateCategoryResponse]:
    """Get all template categories (PUBLIC)."""
    categories = list_categories(db)
    return [TemplateCategoryResponse.model_validate(c) for c in categories]


@router.get("/tags", response_model=List[TemplateTagResponse])
async def get_popular_tags(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(50, ge=1, le=100, description="Maximum tags to return"),
) -> List[TemplateTagResponse]:
    """Get most popular tags (PUBLIC)."""
    tags = list_tags(db, limit=limit)
    return [TemplateTagResponse.model_validate(t) for t in tags]


# ============================================================================
# AUTHENTICATED ENDPOINTS (Require active user)
# ============================================================================


@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def publish_workflow_as_template(
    request: TemplatePublishRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> TemplateResponse:
    """
    Publish a workflow as a marketplace template.
    
    Requires authentication. User must own the workflow.
    Template starts in 'pending' status and requires admin approval.
    """
    try:
        template = publish_template(
            db=db,
            user_id=current_user.id,
            request=request,
        )
        
        # Log user activity
        background_tasks.add_task(
            log_user_activity_task,
            user_id=str(current_user.id),
            action_type="template_published",
            details=f"Published template: {request.title}",
            service_name="Marketplace",
            status="success",
        )
        
        return TemplateResponse.model_validate(template)
    
    except AreaNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except UnauthorizedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except TemplateAlreadyPublishedError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post("/templates/{template_id}/clone", response_model=TemplateCloneResponse)
async def clone_template_to_account(
    template_id: uuid.UUID,
    request: TemplateCloneRequest,
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> TemplateCloneResponse:
    """
    Clone a marketplace template to user's account.
    
    Requires authentication. Template must be approved.
    Creates a new workflow in user's account with steps from template.
    Workflow starts disabled - user must configure service connections.
    """
    try:
        area = clone_template(
            db=db,
            template_id=template_id,
            user_id=current_user.id,
            area_name=request.area_name,
            parameter_overrides=request.parameter_overrides,
        )
        
        # Log user activity
        background_tasks.add_task(
            log_user_activity_task,
            user_id=str(current_user.id),
            action_type="template_cloned",
            details=f"Cloned template: {request.area_name}",
            service_name="Marketplace",
            status="success",
        )
        
        return TemplateCloneResponse(
            created_area_id=area.id,
            message=f"Template cloned successfully as '{area.name}'. Please configure service connections and enable the workflow.",
        )
    
    except TemplateNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except TemplateNotApprovedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


# ============================================================================
# ADMIN ENDPOINTS (Require admin user)
# ============================================================================


@router.post("/admin/templates/{template_id}/approve", response_model=TemplateResponse)
async def approve_template_for_marketplace(
    template_id: uuid.UUID,
    current_admin: Annotated[User, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> TemplateResponse:
    """
    Approve a template for marketplace publication (ADMIN ONLY).
    
    Sets status to 'approved', records approval details, and publishes template.
    """
    try:
        template = approve_template(
            db=db,
            template_id=template_id,
            admin_user_id=current_admin.id,
        )
        
        # Log admin activity
        background_tasks.add_task(
            log_user_activity_task,
            user_id=str(current_admin.id),
            action_type="template_approved",
            details=f"Approved template: {template.title}",
            service_name="Marketplace Admin",
            status="success",
        )
        
        return TemplateResponse.model_validate(template)
    
    except TemplateNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/admin/templates/{template_id}/reject", response_model=TemplateResponse)
async def reject_template_submission(
    template_id: uuid.UUID,
    current_admin: Annotated[User, Depends(require_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> TemplateResponse:
    """
    Reject a template submission (ADMIN ONLY).
    
    Sets status to 'rejected'. Template will not appear in marketplace.
    """
    try:
        template = reject_template(
            db=db,
            template_id=template_id,
            admin_user_id=current_admin.id,
        )
        
        # Log admin activity
        background_tasks.add_task(
            log_user_activity_task,
            user_id=str(current_admin.id),
            action_type="template_rejected",
            details=f"Rejected template: {template.title}",
            service_name="Marketplace Admin",
            status="success",
        )
        
        return TemplateResponse.model_validate(template)
    
    except TemplateNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


__all__ = ["router"]
