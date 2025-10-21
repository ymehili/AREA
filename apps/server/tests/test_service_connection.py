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
    get_user_service_connections,
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


def test_exception_error_messages() -> None:
    """Test exception error messages."""
    # Test ServiceConnectionNotFoundError
    error = ServiceConnectionNotFoundError("test-id-123")
    assert "test-id-123" in str(error)
    assert error.connection_id == "test-id-123"
    
    # Test DuplicateServiceConnectionError
    error2 = DuplicateServiceConnectionError("user-123", "gmail")
    assert "user-123" in str(error2)
    assert "gmail" in str(error2)
    assert error2.user_id == "user-123"
    assert error2.service_name == "gmail"


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


def test_get_user_service_connections_with_uuid(db_session: Session) -> None:
    """Test retrieving service connections with UUID user_id."""
    import uuid
    user_id = uuid.uuid4()
    service_name1 = "google-drive"
    service_name2 = "gmail"

    service_connection_in1 = ServiceConnectionCreate(
        service_name=service_name1,
        access_token="token1",
    )
    service_connection_in2 = ServiceConnectionCreate(
        service_name=service_name2,
        access_token="token2",
    )

    create_service_connection(db_session, service_connection_in1, user_id)
    create_service_connection(db_session, service_connection_in2, user_id)

    # Test with UUID (not string)
    connections = get_user_service_connections(db_session, user_id)

    assert len(connections) == 2
    service_names = [conn.service_name for conn in connections]
    assert service_name1 in service_names
    assert service_name2 in service_names


def test_get_service_connection_by_id_with_uuid(db_session: Session) -> None:
    """Test retrieving a service connection by UUID id."""
    import uuid
    user_id = uuid.uuid4()
    service_name = "google-drive"

    service_connection_in = ServiceConnectionCreate(
        service_name=service_name,
        access_token="test_token",
    )

    connection = create_service_connection(db_session, service_connection_in, user_id)

    # Test with UUID (not string)
    retrieved = get_service_connection_by_id(db_session, connection.id)

    assert retrieved is not None
    assert retrieved.id == connection.id


def test_get_service_connection_by_user_and_service_with_uuid(db_session: Session) -> None:
    """Test retrieving a service connection by UUID user_id."""
    import uuid
    user_id = uuid.uuid4()
    service_name = "google-drive"

    service_connection_in = ServiceConnectionCreate(
        service_name=service_name,
        access_token="test_token",
    )

    created = create_service_connection(db_session, service_connection_in, user_id)

    # Test with UUID (not string)
    retrieved = get_service_connection_by_user_and_service(db_session, user_id, service_name)

    assert retrieved is not None
    assert retrieved.id == created.id


def test_create_service_connection_with_metadata(db_session: Session) -> None:
    """Test creating a service connection with OAuth metadata."""
    user_id = uuid.uuid4()
    service_name = "google-drive"
    access_token = "access_token_123"
    oauth_metadata = {"scope": "full", "provider": "google"}

    service_connection_in = ServiceConnectionCreate(
        service_name=service_name,
        access_token=access_token,
    )

    service_connection = create_service_connection(
        db_session, service_connection_in, user_id, oauth_metadata=oauth_metadata
    )

    assert service_connection.oauth_metadata == oauth_metadata


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


def test_create_api_key_connection(db_session: Session) -> None:
    """Test creating an API key connection."""
    from app.services.service_connections import create_api_key_connection
    
    user_id = uuid.uuid4()
    service_name = "openai"
    api_key = "sk-test-api-key-123"

    connection = create_api_key_connection(db_session, str(user_id), service_name, api_key)

    assert connection.id is not None
    assert connection.user_id == user_id
    assert connection.service_name == service_name
    assert connection.encrypted_access_token != api_key  # Should be encrypted
    assert connection.encrypted_refresh_token is None  # API keys don't have refresh tokens
    assert connection.expires_at is None  # API keys don't expire
    assert connection.oauth_metadata == {"connection_type": "api_key", "service_type": "api_key"}

    # Verify API key is encrypted
    assert decrypt_token(connection.encrypted_access_token) == api_key


def test_create_api_key_connection_duplicate(db_session: Session) -> None:
    """Test creating a duplicate API key connection raises an error."""
    from app.services.service_connections import create_api_key_connection
    
    user_id = uuid.uuid4()
    service_name = "openai"
    api_key = "sk-test-api-key-123"

    # Create the first connection
    create_api_key_connection(db_session, str(user_id), service_name, api_key)

    # Attempt to create a duplicate
    with pytest.raises(DuplicateServiceConnectionError):
        create_api_key_connection(db_session, str(user_id), service_name, api_key)


def test_create_api_key_connection_with_uuid(db_session: Session) -> None:
    """Test creating an API key connection with UUID user_id."""
    from app.services.service_connections import create_api_key_connection
    
    user_id = uuid.uuid4()
    service_name = "openai"
    api_key = "sk-test-api-key-123"

    # Pass UUID directly
    connection = create_api_key_connection(db_session, user_id, service_name, api_key)

    assert connection.user_id == user_id
    assert connection.service_name == service_name


def test_create_service_connection_integrity_error_handling(db_session: Session) -> None:
    """Test that IntegrityError is properly caught and re-raised as DuplicateServiceConnectionError."""
    from sqlalchemy.exc import IntegrityError
    
    user_id = uuid.uuid4()
    service_name = "test-service"
    access_token = "test_token"

    service_connection_in = ServiceConnectionCreate(
        service_name=service_name,
        access_token=access_token,
    )

    # Create the first connection
    create_service_connection(db_session, service_connection_in, user_id)

    # Force the session to commit by trying to create a duplicate
    # The duplicate check should catch it first, but we can test the IntegrityError path
    # by mocking the get_service_connection_by_user_and_service to return None
    with patch('app.services.service_connections.get_service_connection_by_user_and_service', return_value=None):
        with pytest.raises(DuplicateServiceConnectionError):
            create_service_connection(db_session, service_connection_in, user_id)


def test_create_api_key_connection_integrity_error_handling(db_session: Session) -> None:
    """Test that IntegrityError is properly caught in create_api_key_connection."""
    from app.services.service_connections import create_api_key_connection
    
    user_id = uuid.uuid4()
    service_name = "openai"
    api_key = "sk-test-api-key-123"

    # Create the first connection
    create_api_key_connection(db_session, str(user_id), service_name, api_key)

    # Force the session to commit by trying to create a duplicate
    # by mocking the get_service_connection_by_user_and_service to return None
    with patch('app.services.service_connections.get_service_connection_by_user_and_service', return_value=None):
        with pytest.raises(DuplicateServiceConnectionError):
            create_api_key_connection(db_session, str(user_id), service_name, api_key)