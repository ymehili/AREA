"""Repository helpers for interacting with service connection records."""

from __future__ import annotations

from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.service_connection import ServiceConnection
from app.schemas.service_connection import (
    ServiceConnectionCreate,
    ServiceConnectionUpdate,
)
from app.core.encryption import encrypt_token


class ServiceConnectionNotFoundError(Exception):
    """Raised when attempting to access a service connection that doesn't exist."""

    def __init__(self, connection_id: str) -> None:
        super().__init__(f"Service connection with id '{connection_id}' not found")
        self.connection_id = connection_id


class DuplicateServiceConnectionError(Exception):
    """Raised when attempting to create a service connection that already exists for the user and service."""

    def __init__(self, user_id: str, service_name: str) -> None:
        super().__init__(
            f"A service connection for user '{user_id}' and service '{service_name}' already exists"
        )
        self.user_id = user_id
        self.service_name = service_name


def get_service_connection_by_id(
    db: Session, connection_id: str
) -> Optional[ServiceConnection]:
    """Fetch a service connection by its ID."""
    import uuid as uuid_module

    # Convert string connection_id to UUID for proper comparison
    connection_uuid = (
        connection_id
        if isinstance(connection_id, uuid_module.UUID)
        else uuid_module.UUID(connection_id)
    )
    statement = select(ServiceConnection).where(ServiceConnection.id == connection_uuid)
    result = db.execute(statement)
    return result.scalar_one_or_none()


def get_service_connection_by_user_and_service(
    db: Session, user_id: str, service_name: str
) -> Optional[ServiceConnection]:
    """Fetch a service connection by user ID and service name."""
    import uuid as uuid_module

    # Convert string user_id to UUID for proper comparison
    user_uuid = (
        user_id if isinstance(user_id, uuid_module.UUID) else uuid_module.UUID(user_id)
    )
    statement = select(ServiceConnection).where(
        ServiceConnection.user_id == user_uuid,
        ServiceConnection.service_name == service_name,
    )
    result = db.execute(statement)
    return result.scalar_one_or_none()


def get_user_service_connections(db: Session, user_id: str) -> list[ServiceConnection]:
    """Fetch all service connections for a user."""
    import uuid as uuid_module

    # Convert string user_id to UUID for proper comparison
    user_uuid = (
        user_id if isinstance(user_id, uuid_module.UUID) else uuid_module.UUID(user_id)
    )
    statement = select(ServiceConnection).where(ServiceConnection.user_id == user_uuid)
    result = db.execute(statement)
    return list(result.scalars().all())


def create_service_connection(
    db: Session,
    service_connection_in: ServiceConnectionCreate,
    user_id: str,
    oauth_metadata: Optional[Dict[str, Any]] = None,
) -> ServiceConnection:
    """Create a new service connection with encrypted tokens and optional metadata."""
    import uuid as uuid_module

    # Convert string user_id to UUID for proper handling
    user_uuid = (
        user_id if isinstance(user_id, uuid_module.UUID) else uuid_module.UUID(user_id)
    )

    # Check if a connection already exists for this user and service
    existing_connection = get_service_connection_by_user_and_service(
        db, user_id, service_connection_in.service_name
    )
    if existing_connection is not None:
        raise DuplicateServiceConnectionError(
            user_id, service_connection_in.service_name
        )

    # Encrypt tokens before storing
    encrypted_access_token = encrypt_token(service_connection_in.access_token)
    encrypted_refresh_token = (
        encrypt_token(service_connection_in.refresh_token)
        if service_connection_in.refresh_token
        else None
    )

    service_connection = ServiceConnection(
        user_id=user_uuid,
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
        raise DuplicateServiceConnectionError(
            user_id, service_connection_in.service_name
        ) from exc

    db.refresh(service_connection)
    return service_connection


def update_service_connection(
    db: Session, connection_id: str, service_connection_in: ServiceConnectionUpdate
) -> ServiceConnection:
    """Update an existing service connection."""
    service_connection = get_service_connection_by_id(db, connection_id)
    if service_connection is None:
        raise ServiceConnectionNotFoundError(connection_id)

    # Update fields if provided
    if service_connection_in.service_name is not None:
        service_connection.service_name = service_connection_in.service_name

    if service_connection_in.access_token is not None:
        service_connection.encrypted_access_token = (
            encrypt_token(service_connection_in.access_token) or ""
        )

    if service_connection_in.refresh_token is not None:
        service_connection.encrypted_refresh_token = encrypt_token(
            service_connection_in.refresh_token
        )

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


def create_api_key_connection(
    db: Session, user_id: str, service_name: str, api_key: str
) -> ServiceConnection:
    """Create a service connection for API-key based services (not OAuth).

    Args:
        db: Database session
        user_id: User ID to associate with the connection
        service_name: Name of the service (e.g., 'openai')
        api_key: Unencrypted API key that will be encrypted before storage

    Returns:
        Created ServiceConnection object

    Raises:
        DuplicateServiceConnectionError: If a connection already exists for this user and service
    """
    import uuid as uuid_module

    # Convert string user_id to UUID for proper handling
    user_uuid = (
        user_id if isinstance(user_id, uuid_module.UUID) else uuid_module.UUID(user_id)
    )

    # Check if a connection already exists for this user and service
    existing_connection = get_service_connection_by_user_and_service(
        db, user_id, service_name
    )
    if existing_connection is not None:
        raise DuplicateServiceConnectionError(user_id, service_name)

    # Encrypt the API key before storing
    from app.core.encryption import encrypt_token

    encrypted_api_key = encrypt_token(api_key)

    # Create service connection with API key metadata
    service_connection = ServiceConnection(
        user_id=user_uuid,
        service_name=service_name,
        encrypted_access_token=encrypted_api_key,
        # API key connections don't have refresh tokens or expiry
        encrypted_refresh_token=None,
        expires_at=None,
        # Store metadata to indicate this is an API key connection
        oauth_metadata={"connection_type": "api_key", "service_type": "api_key"},
    )

    db.add(service_connection)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateServiceConnectionError(user_id, service_name) from exc

    db.refresh(service_connection)
    return service_connection


def create_rss_connection(
    db: Session,
    user_id: str,
    feed_url: str,
    check_interval: int = 300,
    max_items: int = 10,
) -> ServiceConnection:
    """Create a service connection for RSS feeds.

    Args:
        db: Database session
        user_id: User ID to associate with the connection
        feed_url: RSS feed URL
        check_interval: Polling interval in seconds (default: 300 = 5 minutes)
        max_items: Maximum number of items to process per check (default: 10)

    Returns:
        Created ServiceConnection object

    Raises:
        DuplicateServiceConnectionError: If a connection already exists for this user and service
    """
    import uuid as uuid_module

    # Convert string user_id to UUID for proper handling
    user_uuid = (
        user_id if isinstance(user_id, uuid_module.UUID) else uuid_module.UUID(user_id)
    )

    # Check if a connection already exists for this user and service
    existing_connection = get_service_connection_by_user_and_service(db, user_id, "rss")
    if existing_connection is not None:
        raise DuplicateServiceConnectionError(user_id, "rss")

    # RSS connections don't use access tokens - store empty string
    from app.core.encryption import encrypt_token

    encrypted_empty_token = encrypt_token("")

    # Create service connection with RSS-specific metadata
    service_connection = ServiceConnection(
        user_id=user_uuid,
        service_name="rss",
        encrypted_access_token=encrypted_empty_token,
        # RSS connections don't have refresh tokens or expiry
        encrypted_refresh_token=None,
        expires_at=None,
        # Store RSS-specific metadata
        oauth_metadata={
            "connection_type": "rss_url",
            "feed_url": feed_url.strip(),
            "check_interval": check_interval,
            "max_items": max_items,
            "service_type": "rss",
        },
    )

    db.add(service_connection)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateServiceConnectionError(user_id, "rss") from exc

    db.refresh(service_connection)
    return service_connection


def validate_rss_feed_url(feed_url: str) -> dict[str, Any]:
    """Validate an RSS feed URL without database operations.

    Args:
        feed_url: RSS feed URL to validate

    Returns:
        Dictionary containing validation results

    Raises:
        ValueError: If the RSS feed URL is invalid
    """
    import httpx
    import feedparser

    # Basic URL validation
    if not feed_url or not feed_url.strip():
        raise ValueError("RSS feed URL is required")

    feed_url = feed_url.strip()

    if not (feed_url.startswith("http://") or feed_url.startswith("https://")):
        raise ValueError(
            "Invalid RSS feed URL. URL must start with http:// or https://"
        )

    # Test the RSS feed by parsing it
    try:
        # Use httpx with timeout for network requests
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(feed_url)
            response.raise_for_status()

        # Parse RSS feed using feedparser
        feed = feedparser.parse(response.content)

        if feed.bozo:
            # Feed is malformed but might still contain usable data
            pass

        # Validate feed has required structure
        if not hasattr(feed, "feed") or not hasattr(feed, "entries"):
            raise ValueError("Invalid RSS feed structure")

        # Extract feed information
        feed_info = {
            "title": getattr(feed.feed, "title", "Unknown Feed"),
            "description": getattr(feed.feed, "description", ""),
            "link": getattr(feed.feed, "link", ""),
            "language": getattr(feed.feed, "language", ""),
            "updated": getattr(feed.feed, "updated", ""),
            "generator": getattr(feed.feed, "generator", ""),
            "total_items": len(feed.entries) if feed.entries else 0,
            "url": feed_url,
            "bozo": feed.bozo,
            "bozo_exception": str(feed.bozo_exception) if feed.bozo_exception else None,
        }

        return {"valid": True, "feed_info": feed_info}

    except httpx.RequestError as e:
        raise ValueError(f"Failed to fetch RSS feed: {str(e)}")
    except Exception as e:
        if "timeout" in str(e).lower():
            raise ValueError(
                "Request timed out while fetching RSS feed. The feed server may be slow or unavailable."
            )
        elif "404" in str(e) or "not found" in str(e).lower():
            raise ValueError(
                "RSS feed not found. Please check the URL and ensure it's accessible."
            )
        elif "401" in str(e) or "unauthorized" in str(e).lower():
            raise ValueError(
                "RSS feed requires authentication. AREA currently supports public RSS feeds only."
            )
        elif "403" in str(e) or "forbidden" in str(e).lower():
            raise ValueError(
                "Access to RSS feed is forbidden. The server may be blocking requests."
            )
        else:
            raise ValueError(f"Failed to validate RSS feed: {str(e)}")


def get_rss_feed_info_from_connection(connection: ServiceConnection) -> dict[str, Any]:
    """Extract RSS feed information from a service connection.

    Args:
        connection: ServiceConnection object for RSS service

    Returns:
        Dictionary containing RSS feed information

    Raises:
        ValueError: If connection is not an RSS connection or missing required data
    """
    if connection.service_name != "rss":
        raise ValueError("Connection is not for RSS service")

    if (
        not connection.oauth_metadata
        or connection.oauth_metadata.get("connection_type") != "rss_url"
    ):
        raise ValueError("Invalid RSS connection metadata")

    feed_url = connection.oauth_metadata.get("feed_url")
    if not feed_url:
        raise ValueError("RSS feed URL not found in connection metadata")

    return {
        "feed_url": feed_url,
        "check_interval": connection.oauth_metadata.get("check_interval", 300),
        "max_items": connection.oauth_metadata.get("max_items", 10),
        "connection_type": connection.oauth_metadata.get("connection_type"),
        "service_type": connection.oauth_metadata.get("service_type", "rss"),
    }


__all__ = [
    "ServiceConnectionNotFoundError",
    "DuplicateServiceConnectionError",
    "create_service_connection",
    "create_api_key_connection",
    "create_rss_connection",
    "validate_rss_feed_url",
    "get_rss_feed_info_from_connection",
    "get_service_connection_by_id",
    "get_service_connection_by_user_and_service",
    "get_user_service_connections",
    "update_service_connection",
    "delete_service_connection",
]
