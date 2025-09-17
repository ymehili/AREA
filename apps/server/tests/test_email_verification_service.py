"""Unit tests for email verification token service helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.email_verification_token import EmailVerificationToken
from app.models.user import User
from app.services.email_verification import (
    EmailVerificationTokenAlreadyUsedError,
    EmailVerificationTokenExpiredError,
    EmailVerificationTokenInvalidError,
    confirm_user_by_token,
    issue_confirmation_token,
)


def _create_user(db_session) -> User:
    user = User(email="service@example.com", hashed_password="hashed")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_issue_confirmation_token_persists_hashed_value(db_session) -> None:
    user = _create_user(db_session)

    raw_token = issue_confirmation_token(db_session, user)
    db_session.commit()

    stored_token = db_session.execute(
        select(EmailVerificationToken).where(EmailVerificationToken.user_id == user.id)
    ).scalar_one()
    assert stored_token.token_hash != raw_token
    assert stored_token.consumed_at is None
    assert user.confirmation_sent_at is not None


def test_issue_confirmation_token_invalidates_previous_tokens(db_session) -> None:
    user = _create_user(db_session)

    first = issue_confirmation_token(db_session, user)
    db_session.commit()

    second = issue_confirmation_token(db_session, user)
    db_session.commit()

    tokens = db_session.execute(
        select(EmailVerificationToken)
        .where(EmailVerificationToken.user_id == user.id)
        .order_by(EmailVerificationToken.created_at)
    ).scalars().all()
    assert len(tokens) == 2
    assert tokens[0].consumed_at is not None
    assert tokens[1].consumed_at is None
    assert tokens[0].token_hash != tokens[1].token_hash
    assert second != first


def test_confirm_user_by_token_marks_user_confirmed(db_session) -> None:
    user = _create_user(db_session)
    raw_token = issue_confirmation_token(db_session, user)
    db_session.commit()

    confirmed_user = confirm_user_by_token(db_session, raw_token)
    db_session.commit()

    assert confirmed_user.is_confirmed is True
    assert confirmed_user.confirmed_at is not None
    token = db_session.execute(select(EmailVerificationToken)).scalar_one()
    assert token.consumed_at is not None


def test_confirm_user_by_token_rejects_expired(db_session) -> None:
    user = _create_user(db_session)
    raw_token = issue_confirmation_token(db_session, user)
    token = db_session.execute(select(EmailVerificationToken)).scalar_one()
    token.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    with pytest.raises(EmailVerificationTokenExpiredError):
        confirm_user_by_token(db_session, raw_token)


def test_confirm_user_by_token_rejects_consumed_tokens(db_session) -> None:
    user = _create_user(db_session)
    raw_token = issue_confirmation_token(db_session, user)
    db_session.commit()

    confirm_user_by_token(db_session, raw_token)
    db_session.commit()

    with pytest.raises(EmailVerificationTokenAlreadyUsedError):
        confirm_user_by_token(db_session, raw_token)


def test_confirm_user_by_token_rejects_unknown_token(db_session) -> None:
    user = _create_user(db_session)
    issue_confirmation_token(db_session, user)
    db_session.commit()

    with pytest.raises(EmailVerificationTokenInvalidError):
        confirm_user_by_token(db_session, "invalid-token")
