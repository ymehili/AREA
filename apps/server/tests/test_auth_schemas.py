"""Tests for authentication schemas."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.models.user import User
from app.schemas.auth import UserRead


def test_user_read_includes_confirmation_fields() -> None:
    now = datetime.now(timezone.utc)
    user = User(
        email="schema@example.com",
        hashed_password="hashed",
        is_confirmed=True,
        confirmed_at=now,
    )
    user.id = uuid.uuid4()
    user.created_at = now
    user.updated_at = now

    serialized = UserRead.model_validate(user)
    assert serialized.is_confirmed is True
    assert serialized.confirmed_at == now
    assert serialized.email == "schema@example.com"
