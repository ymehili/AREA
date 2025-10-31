"""Service layer for marketplace template operations."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.area import Area
from app.models.area_step import AreaStep
from app.models.marketplace_template import PublishedTemplate
from app.models.template_category import TemplateCategory
from app.models.template_tag import TemplateTag
from app.models.template_usage import TemplateUsage
from app.schemas.marketplace import TemplatePublishRequest


# Custom Exceptions
class AreaNotFoundError(Exception):
    """Raised when the area to publish doesn't exist."""

    def __init__(self, area_id: str) -> None:
        super().__init__(f"Area with id '{area_id}' not found")
        self.area_id = area_id


class TemplateNotFoundError(Exception):
    """Raised when a template doesn't exist."""

    def __init__(self, template_id: str) -> None:
        super().__init__(f"Template with id '{template_id}' not found")
        self.template_id = template_id


class TemplateAlreadyPublishedError(Exception):
    """Raised when attempting to publish an area that's already published."""

    def __init__(self, area_id: str) -> None:
        super().__init__(f"Area '{area_id}' has already been published as a template")
        self.area_id = area_id


class UnauthorizedError(Exception):
    """Raised when user doesn't own the resource."""

    def __init__(self, message: str = "You don't have permission to access this resource") -> None:
        super().__init__(message)


class TemplateNotApprovedError(Exception):
    """Raised when attempting to clone a template that's not approved."""

    def __init__(self, template_id: str, status: str) -> None:
        super().__init__(f"Template '{template_id}' is not approved (current status: {status})")
        self.template_id = template_id
        self.status = status


def sanitize_template(area: Area, steps: List[AreaStep]) -> Dict[str, Any]:
    """
    Sanitize area and steps to create a template JSON.
    
    CRITICAL SECURITY: This function removes all credentials from the template.
    Templates must never contain actual service connection IDs or tokens.
    """
    template = {
        "name": area.name,
        "trigger": {
            "service": area.trigger_service,
            "action": area.trigger_action,
            "params": area.trigger_params if area.trigger_params else {},
            # Replace service connection with placeholder
            "credential_placeholder": f"{{{{user_credential:{area.trigger_service}}}}}",
        },
        "reaction": {
            "service": area.reaction_service,
            "action": area.reaction_action,
            "params": area.reaction_params if area.reaction_params else {},
            # Replace service connection with placeholder
            "credential_placeholder": f"{{{{user_credential:{area.reaction_service}}}}}",
        },
        "steps": [],
    }

    # Process each step, removing credentials
    for step in steps:
        step_data = {
            "step_type": step.step_type,
            "order": step.order,
            "service": step.service,
            "action": step.action,
            "config": {},
        }

        if step.config:
            # Deep copy config and remove credentials
            step_config = step.config.copy()
            
            # Remove ALL credential-related fields (comprehensive list)
            credential_fields = [
                "service_connection_id",
                "access_token",
                "refresh_token",
                "encrypted_access_token",
                "encrypted_refresh_token",
                "api_key",
                "secret",
                "password",
                "token",
                "credentials",
            ]
            for field in credential_fields:
                step_config.pop(field, None)
            
            # Add credential placeholder if service exists
            if step.service:
                step_data["credential_placeholder"] = f"{{{{user_credential:{step.service}}}}}"
            
            step_data["config"] = step_config

        template["steps"].append(step_data)

    # CRITICAL SECURITY CHECK: Verify no credentials leaked
    template_str = json.dumps(template)
    if "service_connection_id" in template_str:
        raise ValueError("SECURITY VIOLATION: service_connection_id found in template JSON!")
    if "access_token" in template_str:
        raise ValueError("SECURITY VIOLATION: access_token found in template JSON!")
    if "encrypted_access_token" in template_str:
        raise ValueError("SECURITY VIOLATION: encrypted_access_token found in template JSON!")

    return template


def publish_template(
    db: Session,
    user_id: uuid.UUID,
    request: TemplatePublishRequest,
) -> PublishedTemplate:
    """
    Publish an area as a marketplace template.
    
    Steps:
    1. Verify user owns the area
    2. Check if area is already published
    3. Serialize area to sanitized template JSON
    4. Create PublishedTemplate record
    5. Create/associate tags
    """
    # Fetch the area
    area = db.get(Area, request.area_id)
    if not area:
        raise AreaNotFoundError(str(request.area_id))

    # Verify ownership
    if area.user_id != user_id:
        raise UnauthorizedError("You can only publish your own workflows")

    # Check if already published
    existing = db.execute(
        select(PublishedTemplate).where(PublishedTemplate.original_area_id == area.id)
    ).scalar_one_or_none()
    if existing:
        raise TemplateAlreadyPublishedError(str(area.id))

    # Fetch area steps
    steps = db.execute(
        select(AreaStep)
        .where(AreaStep.area_id == area.id)
        .order_by(AreaStep.order)
    ).scalars().all()

    # Sanitize and create template JSON
    template_json = sanitize_template(area, list(steps))

    # Create published template (auto-approved for now - add admin review later if needed)
    template = PublishedTemplate(
        original_area_id=area.id,
        publisher_user_id=user_id,
        title=request.title,
        description=request.description,
        long_description=request.long_description,
        category=request.category,
        template_json=template_json,
        status="approved",  # Auto-approve templates
        visibility="public",
        approved_at=datetime.now(),  # Set approval timestamp
        published_at=datetime.now(),  # Set publication timestamp
    )
    db.add(template)
    db.flush()  # Get template ID

    # Create or find tags and associate them
    for tag_name in request.tags:
        tag_slug = tag_name.lower().replace(" ", "-")
        
        # Try to find existing tag
        existing_tag = db.execute(
            select(TemplateTag).where(TemplateTag.name == tag_name)
        ).scalar_one_or_none()
        
        if existing_tag:
            tag = existing_tag
            # Increment usage count
            tag.usage_count += 1
        else:
            # Create new tag
            tag = TemplateTag(
                name=tag_name,
                slug=tag_slug,
                usage_count=1,
            )
            db.add(tag)
            db.flush()

        # Associate tag with template
        template.tags.append(tag)

    db.commit()
    db.refresh(template)
    return template


def search_templates(
    db: Session,
    query: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    min_rating: Optional[float] = None,
    sort_by: str = "usage_count",
    order: str = "desc",
    offset: int = 0,
    limit: int = 20,
) -> Tuple[List[PublishedTemplate], int]:
    """
    Search and filter marketplace templates.
    
    Uses PostgreSQL full-text search for query matching when available,
    falls back to LIKE search for other databases (e.g., SQLite in tests).
    Only returns approved and public templates.
    """
    # Base query: only approved and public templates
    stmt = select(PublishedTemplate).where(
        PublishedTemplate.status == "approved",
        PublishedTemplate.visibility == "public",
    )

    # Full-text search (PostgreSQL) or LIKE search (SQLite)
    if query:
        clean_query = query.replace("'", "").strip()
        if clean_query:
            # Check if database supports TSVECTOR (PostgreSQL)
            dialect_name = db.bind.dialect.name if db.bind else "postgresql"
            
            if dialect_name == "postgresql":
                # Use full-text search with to_tsquery
                stmt = stmt.where(
                    PublishedTemplate.search_vector.op("@@")(
                        func.to_tsquery("english", clean_query)
                    )
                )
            else:
                # Fallback to LIKE search for SQLite/other databases
                search_pattern = f"%{clean_query}%"
                stmt = stmt.where(
                    (PublishedTemplate.title.ilike(search_pattern)) |
                    (PublishedTemplate.description.ilike(search_pattern))
                )

    # Category filter
    if category:
        stmt = stmt.where(PublishedTemplate.category == category)

    # Tag filter (templates must have ALL specified tags)
    if tags and len(tags) > 0:
        for tag_name in tags:
            stmt = stmt.join(PublishedTemplate.tags).where(TemplateTag.name == tag_name)

    # Rating filter
    if min_rating is not None:
        stmt = stmt.where(PublishedTemplate.rating_average >= min_rating)

    # Count total matching templates (before pagination)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0

    # Sorting
    sort_column = getattr(PublishedTemplate, sort_by, PublishedTemplate.usage_count)
    if order == "desc":
        stmt = stmt.order_by(sort_column.desc())
    else:
        stmt = stmt.order_by(sort_column.asc())

    # Pagination
    stmt = stmt.offset(offset).limit(limit)

    # Execute query
    result = db.execute(stmt)
    templates = result.scalars().unique().all()  # .unique() needed after join

    return list(templates), total


def get_template_by_id(db: Session, template_id: uuid.UUID) -> Optional[PublishedTemplate]:
    """Fetch a template by ID."""
    return db.get(PublishedTemplate, template_id)


def list_categories(db: Session) -> List[TemplateCategory]:
    """Get all template categories ordered by display_order."""
    stmt = select(TemplateCategory).order_by(TemplateCategory.display_order)
    result = db.execute(stmt)
    return list(result.scalars().all())


def list_tags(db: Session, limit: int = 50) -> List[TemplateTag]:
    """Get most popular tags."""
    stmt = select(TemplateTag).order_by(TemplateTag.usage_count.desc()).limit(limit)
    result = db.execute(stmt)
    return list(result.scalars().all())


def clone_template(
    db: Session,
    template_id: uuid.UUID,
    user_id: uuid.UUID,
    area_name: str,
    parameter_overrides: Optional[Dict[str, Any]] = None,
) -> Area:
    """
    Clone a template to user's account with proper step ID remapping.
    
    Following the pattern from areas.py:45-75 for ID remapping.
    
    Steps:
    1. Fetch template and verify it's approved
    2. Deserialize template JSON
    3. Create new Area for user
    4. Create all AreaSteps with temporary client IDs
    5. Build mapping: {clientId: serverUUID}
    6. Update all config.targets arrays with real UUIDs
    7. Record TemplateUsage and increment counters
    """
    # Fetch template
    template = db.get(PublishedTemplate, template_id)
    if not template:
        raise TemplateNotFoundError(str(template_id))

    # Verify template is approved
    if template.status != "approved":
        raise TemplateNotApprovedError(str(template_id), template.status)

    template_data = template.template_json
    parameter_overrides = parameter_overrides or {}

    # Phase 1: Create Area
    area = Area(
        user_id=user_id,
        name=area_name,
        trigger_service=template_data["trigger"]["service"],
        trigger_action=template_data["trigger"]["action"],
        trigger_params=template_data["trigger"].get("params", {}),
        reaction_service=template_data["reaction"]["service"],
        reaction_action=template_data["reaction"]["action"],
        reaction_params=template_data["reaction"].get("params", {}),
        enabled=False,  # Start disabled - user needs to configure credentials
    )
    db.add(area)
    db.flush()  # Get area.id

    # Phase 2: Create all steps with temporary client IDs
    client_id_to_step = {}
    steps_data = template_data.get("steps", [])
    
    for step_data in steps_data:
        # Generate a client ID for this step (use order as fallback)
        client_id = step_data.get("config", {}).get("clientId", f"order_{step_data['order']}")
        
        step = AreaStep(
            area_id=area.id,
            step_type=step_data.get("step_type", "action"),
            order=step_data.get("order", 0),
            service=step_data.get("service"),
            action=step_data.get("action"),
            config=step_data.get("config", {}).copy() if step_data.get("config") else {},
        )
        db.add(step)
        db.flush()  # Get step.id
        client_id_to_step[str(client_id)] = step

    # Phase 3: Build ID mapping and update targets
    id_mapping = {client_id: str(step.id) for client_id, step in client_id_to_step.items()}

    for step in client_id_to_step.values():
        if step.config and "targets" in step.config and isinstance(step.config["targets"], list):
            # Remap all target IDs
            updated_targets = []
            for target_id in step.config["targets"]:
                new_target_id = id_mapping.get(str(target_id), str(target_id))
                updated_targets.append(new_target_id)
            
            # Update the step's config with new targets
            step.config = {**step.config, "targets": updated_targets}
        
        # Remove temporary clientId
        if step.config:
            step.config.pop("clientId", None)

    # Record template usage
    usage = TemplateUsage(
        template_id=template_id,
        user_id=user_id,
        created_area_id=area.id,
    )
    db.add(usage)

    # Increment template counters
    template.usage_count += 1
    template.clone_count += 1

    db.commit()
    db.refresh(area)
    return area


def approve_template(
    db: Session,
    template_id: uuid.UUID,
    admin_user_id: uuid.UUID,
) -> PublishedTemplate:
    """Approve a template for marketplace publication."""
    template = db.get(PublishedTemplate, template_id)
    if not template:
        raise TemplateNotFoundError(str(template_id))

    template.status = "approved"
    template.approved_at = datetime.now()
    template.approved_by_user_id = admin_user_id
    template.published_at = datetime.now()

    db.commit()
    db.refresh(template)
    return template


def reject_template(
    db: Session,
    template_id: uuid.UUID,
    admin_user_id: uuid.UUID,
) -> PublishedTemplate:
    """Reject a template."""
    template = db.get(PublishedTemplate, template_id)
    if not template:
        raise TemplateNotFoundError(str(template_id))

    template.status = "rejected"
    template.approved_by_user_id = admin_user_id

    db.commit()
    db.refresh(template)
    return template


__all__ = [
    "publish_template",
    "search_templates",
    "get_template_by_id",
    "list_categories",
    "list_tags",
    "clone_template",
    "approve_template",
    "reject_template",
    "sanitize_template",
    "AreaNotFoundError",
    "TemplateNotFoundError",
    "TemplateAlreadyPublishedError",
    "UnauthorizedError",
    "TemplateNotApprovedError",
]
