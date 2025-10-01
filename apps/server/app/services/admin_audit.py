"""Service functions for admin audit logging."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.admin_audit_log import AdminAuditLog
from app.schemas.admin_audit_log import AdminAuditLogCreate


def create_admin_audit_log(
    db: Session,
    admin_user_id: UUID,
    target_user_id: UUID,
    action_type: str,
    details: Optional[str] = None
) -> AdminAuditLog:
    """Create a new admin audit log entry."""
    
    audit_log = AdminAuditLog(
        admin_user_id=admin_user_id,
        target_user_id=target_user_id,
        action_type=action_type,
        details=details,
    )
    
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)
    
    return audit_log


__all__ = [
    "create_admin_audit_log",
]