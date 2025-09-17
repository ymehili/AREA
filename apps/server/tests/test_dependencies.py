import pytest
from fastapi import HTTPException

from app.api.dependencies.auth import require_active_user
from app.core.security import create_access_token
from app.schemas.auth import UserCreate
from app.services import create_user


def test_require_active_user_returns_user(db_session):
    user = create_user(
        db_session,
        UserCreate(email="dep@example.com", password="password123"),
        email_sender=lambda *_: None,
    )
    user.is_confirmed = True
    db_session.commit()
    token = create_access_token(subject=str(user.id))
    current_user = require_active_user(token=token, db=db_session)
    assert current_user.id == user.id


def test_require_active_user_rejects_invalid_token(db_session):
    with pytest.raises(HTTPException):
        require_active_user(token="invalid", db=db_session)
