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


def test_create_access_token_with_extra_claims():
    """Test creating access token with extra claims."""
    from jose import jwt
    from app.core.config import settings
    
    subject = "test-user-id"
    extra_claims = {"custom_claim": "custom_value", "role": "admin"}
    
    token = create_access_token(subject=subject, extra_claims=extra_claims)
    
    # Decode the token to verify claims
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    
    assert payload["sub"] == subject
    assert payload["custom_claim"] == "custom_value"
    assert payload["role"] == "admin"
    assert "exp" in payload
