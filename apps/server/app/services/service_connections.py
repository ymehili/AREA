"""Repository helpers for interacting with service connection records."""

from __future__ import annotations

from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.service_connection import ServiceConnection
from app.schemas.service_connection import ServiceConnectionCreate, ServiceConnectionUpdate
from app.core.encryption import encrypt_token


class ServiceConnectionNotFoundError(Exception):
    """Raised when attempting to access a service connection that doesn't exist."""

    def __init__(self, connection_id: str) -> None:
        super().__init__(f"Service connection with id '{connection_id}' not found")
        self.connection_id = connection_id


class DuplicateServiceConnectionError(Exception):
    """Raised when attempting to create a service connection that already exists for the user and service."""

    def __init__(self, user_id: str, service_name: str) -> None:
        super().__init__(f"A service connection for user '{user_id}' and service '{service_name}' already exists")
        self.user_id = user_id
        self.service_name = service_name


def get_service_connection_by_id(db: Session, connection_id: str) -> Optional[ServiceConnection]:
    """Fetch a service connection by its ID."""
    statement = select(ServiceConnection).where(ServiceConnection.id == connection_id)
    result = db.execute(statement)
    return result.scalar_one_or_none()


def get_service_connection_by_user_and_service(db: Session, user_id: str, service_name: str) -> Optional[ServiceConnection]:
    """Fetch a service connection by user ID and service name."""
    statement = select(ServiceConnection).where(
        ServiceConnection.user_id == user_id,
        ServiceConnection.service_name == service_name
    )
    result = db.execute(statement)
    return result.scalar_one_or_none()


def get_user_service_connections(db: Session, user_id: str) -> list[ServiceConnection]:
    """Fetch all service connections for a user."""
    statement = select(ServiceConnection).where(ServiceConnection.user_id == user_id)
    result = db.execute(statement)
    return list(result.scalars().all())


def create_service_connection(
    db: Session,
    service_connection_in: ServiceConnectionCreate,
    user_id: str,
    oauth_metadata: Optional[Dict[str, Any]] = None
) -> ServiceConnection:
    """Create a new service connection with encrypted tokens and optional metadata."""
    # Check if a connection already exists for this user and service
    existing_connection = get_service_connection_by_user_and_service(db, user_id, service_connection_in.service_name)
    if existing_connection is not None:
        raise DuplicateServiceConnectionError(user_id, service_connection_in.service_name)

    # Encrypt tokens before storing
    encrypted_access_token = encrypt_token(service_connection_in.access_token)
    encrypted_refresh_token = encrypt_token(service_connection_in.refresh_token) if service_connection_in.refresh_token else None

    service_connection = ServiceConnection(
        user_id=user_id,
        service_name=service_connection_in.service_name,
        encrypted_access_token=encrypted_access_token,
        encrypted_refresh_token=encrypted_refresh_token,
        expires_at=service_connection_in.expires_at,
        oauth_metadata=oauth_metadata,
    )

    db.add(service_connection)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateServiceConnectionError(user_id, service_connection_in.service_name) from exc

    db.refresh(service_connection)
    return service_connection


def update_service_connection(db: Session, connection_id: str, service_connection_in: ServiceConnectionUpdate) -> ServiceConnection:
    """Update an existing service connection."""
    service_connection = get_service_connection_by_id(db, connection_id)
    if service_connection is None:
        raise ServiceConnectionNotFoundError(connection_id)

    # Update fields if provided
    if service_connection_in.service_name is not None:
        service_connection.service_name = service_connection_in.service_name

    if service_connection_in.access_token is not None:
        service_connection.encrypted_access_token = encrypt_token(service_connection_in.access_token) or ""

    if service_connection_in.refresh_token is not None:
        service_connection.encrypted_refresh_token = encrypt_token(service_connection_in.refresh_token)

    if service_connection_in.expires_at is not None:
        service_connection.expires_at = service_connection_in.expires_at

    db.commit()
    db.refresh(service_connection)
    return service_connection


def delete_service_connection(db: Session, connection_id: str) -> bool:
    """Delete a service connection by its ID."""
    service_connection = get_service_connection_by_id(db, connection_id)
    if service_connection is None:
        return False

    db.delete(service_connection)
    db.commit()
    return True


__all__ = [
    "ServiceConnectionNotFoundError",
    "DuplicateServiceConnectionError",
    "create_service_connection",
    "get_service_connection_by_id",
    "get_service_connection_by_user_and_service",
    "get_user_service_connections",
    "update_service_connection",
    "delete_service_connection",
]
