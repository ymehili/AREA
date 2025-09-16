"""Tests for service connection model, services, and encryption."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.core.encryption import encrypt_token, decrypt_token
from app.models.service_connection import ServiceConnection
from app.schemas.service_connection import ServiceConnectionCreate, ServiceConnectionUpdate
from app.services.service_connections import (
    create_service_connection,
    get_service_connection_by_id,
    get_service_connection_by_user_and_service,
    update_service_connection,
    delete_service_connection,
    ServiceConnectionNotFoundError,
    DuplicateServiceConnectionError,
)


def test_encrypt_decrypt_token() -> None:
    """Test that tokens can be encrypted and decrypted correctly."""
    token = "test_token_123"
    encrypted = encrypt_token(token)
    assert encrypted is not None
    assert encrypted != token  # Should be encrypted

    decrypted = decrypt_token(encrypted)
    assert decrypted == token


def test_encrypt_decrypt_none_token() -> None:
    """Test that encrypting/decrypting None returns None."""
    assert encrypt_token(None) is None
    assert decrypt_token(None) is None


def test_create_service_connection(db_session: Session) -> None:
    """Test creating a new service connection."""
    user_id = uuid.uuid4()
    service_name = "google-drive"
    access_token = "access_token_123"
    refresh_token = "refresh_token_123"
    expires_at = datetime.now() + timedelta(hours=1)

    service_connection_in = ServiceConnectionCreate(
        service_name=service_name,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )

    service_connection = create_service_connection(db_session, service_connection_in, user_id)

    assert service_connection.id is not None
    assert service_connection.user_id == user_id
    assert service_connection.service_name == service_name
    assert service_connection.encrypted_access_token != access_token  # Should be encrypted
    assert service_connection.encrypted_refresh_token != refresh_token  # Should be encrypted
    assert service_connection.expires_at == expires_at

    # Verify tokens are encrypted
    assert decrypt_token(service_connection.encrypted_access_token) == access_token
    assert decrypt_token(service_connection.encrypted_refresh_token) == refresh_token


def test_create_duplicate_service_connection(db_session: Session) -> None:
    """Test that creating a duplicate service connection raises an error."""
    user_id = uuid.uuid4()
    service_name = "google-drive"
    access_token = "access_token_123"

    service_connection_in = ServiceConnectionCreate(
        service_name=service_name,
        access_token=access_token,
    )

    # Create the first connection
    create_service_connection(db_session, service_connection_in, user_id)

    # Attempt to create a duplicate
    with pytest.raises(DuplicateServiceConnectionError):
        create_service_connection(db_session, service_connection_in, user_id)


def test_get_service_connection_by_id(db_session: Session) -> None:
    """Test retrieving a service connection by ID."""
    user_id = uuid.uuid4()
    service_name = "google-drive"
    access_token = "access_token_123"

    service_connection_in = ServiceConnectionCreate(
        service_name=service_name,
        access_token=access_token,
    )

    created_connection = create_service_connection(db_session, service_connection_in, user_id)
    retrieved_connection = get_service_connection_by_id(db_session, created_connection.id)

    assert retrieved_connection is not None
    assert retrieved_connection.id == created_connection.id
    assert retrieved_connection.user_id == user_id
    assert retrieved_connection.service_name == service_name


def test_get_service_connection_by_user_and_service(db_session: Session) -> None:
    """Test retrieving a service connection by user ID and service name."""
    user_id = uuid.uuid4()
    service_name = "google-drive"
    access_token = "access_token_123"

    service_connection_in = ServiceConnectionCreate(
        service_name=service_name,
        access_token=access_token,
    )

    created_connection = create_service_connection(db_session, service_connection_in, user_id)
    retrieved_connection = get_service_connection_by_user_and_service(db_session, user_id, service_name)

    assert retrieved_connection is not None
    assert retrieved_connection.id == created_connection.id
    assert retrieved_connection.user_id == user_id
    assert retrieved_connection.service_name == service_name


def test_update_service_connection(db_session: Session) -> None:
    """Test updating a service connection."""
    user_id = uuid.uuid4()
    service_name = "google-drive"
    access_token = "access_token_123"
    refresh_token = "refresh_token_123"

    service_connection_in = ServiceConnectionCreate(
        service_name=service_name,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    created_connection = create_service_connection(db_session, service_connection_in, user_id)

    # Update the connection
    new_service_name = "dropbox"
    new_access_token = "new_access_token_123"
    new_refresh_token = "new_refresh_token_123"
    new_expires_at = datetime.now() + timedelta(hours=2)

    service_connection_update = ServiceConnectionUpdate(
        service_name=new_service_name,
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_at=new_expires_at,
    )

    updated_connection = update_service_connection(db_session, created_connection.id, service_connection_update)

    assert updated_connection.id == created_connection.id
    assert updated_connection.user_id == user_id
    assert updated_connection.service_name == new_service_name
    assert updated_connection.expires_at == new_expires_at
    assert updated_connection.encrypted_access_token != new_access_token  # Should be encrypted
    assert updated_connection.encrypted_refresh_token != new_refresh_token  # Should be encrypted

    # Verify tokens are encrypted
    assert decrypt_token(updated_connection.encrypted_access_token) == new_access_token
    assert decrypt_token(updated_connection.encrypted_refresh_token) == new_refresh_token


def test_update_nonexistent_service_connection(db_session: Session) -> None:
    """Test updating a nonexistent service connection raises an error."""
    connection_id = uuid.uuid4()
    service_connection_update = ServiceConnectionUpdate(
        service_name="new-service",
    )

    with pytest.raises(ServiceConnectionNotFoundError):
        update_service_connection(db_session, connection_id, service_connection_update)


def test_delete_service_connection(db_session: Session) -> None:
    """Test deleting a service connection."""
    user_id = uuid.uuid4()
    service_name = "google-drive"
    access_token = "access_token_123"

    service_connection_in = ServiceConnectionCreate(
        service_name=service_name,
        access_token=access_token,
    )

    created_connection = create_service_connection(db_session, service_connection_in, user_id)
    assert get_service_connection_by_id(db_session, created_connection.id) is not None

    # Delete the connection
    result = delete_service_connection(db_session, created_connection.id)
    assert result is True

    # Verify it's deleted
    assert get_service_connection_by_id(db_session, created_connection.id) is None


def test_delete_nonexistent_service_connection(db_session: Session) -> None:
    """Test deleting a nonexistent service connection returns False."""
    connection_id = uuid.uuid4()
    result = delete_service_connection(db_session, connection_id)
    assert result is False