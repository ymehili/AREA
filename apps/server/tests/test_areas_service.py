"""Tests for areas service."""

from __future__ import annotations

import uuid
import pytest
from sqlalchemy.orm import Session

from app.models.area import Area
from app.schemas.area import AreaCreate
from app.services.areas import (
    AreaNotFoundError,
    DuplicateAreaError,
    create_area,
    get_area_by_id,
)


def test_area_not_found_error():
    """Test AreaNotFoundError exception."""
    error = AreaNotFoundError("test-area-id")
    assert "test-area-id" in str(error)
    assert error.area_id == "test-area-id"


def test_duplicate_area_error():
    """Test DuplicateAreaError exception."""
    error = DuplicateAreaError("user-123", "My Area")
    assert "user-123" in str(error)
    assert "My Area" in str(error)
    assert error.user_id == "user-123"
    assert error.name == "My Area"


def test_create_duplicate_area(db_session: Session):
    """Test that creating a duplicate area raises an error."""
    user_id = str(uuid.uuid4())
    area_name = "Test Area"

    area_in = AreaCreate(
        name=area_name,
        trigger_service="time",
        trigger_action="every_interval",
        reaction_service="debug",
        reaction_action="log",
        enabled=True,
    )

    # Create the first area
    create_area(db_session, area_in, user_id)

    # Attempt to create a duplicate
    with pytest.raises(DuplicateAreaError):
        create_area(db_session, area_in, user_id)


def test_get_area_by_id_not_found(db_session: Session):
    """Test getting an area that doesn't exist."""
    non_existent_id = str(uuid.uuid4())
    
    result = get_area_by_id(db_session, non_existent_id)
    
    assert result is None

