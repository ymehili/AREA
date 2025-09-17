"""Unit tests for user service helpers."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.profile import PasswordChangeRequest, UserProfileUpdate
from app.services.users import (
    IncorrectPasswordError,
    LastLoginMethodRemovalError,
    LoginProviderAlreadyLinkedError,
    LoginProviderNotLinkedError,
    UserEmailAlreadyExistsError,
    change_user_password,
    link_login_provider,
    unlink_login_provider,
    update_user_profile,
)


def _create_user(db: Session, email: str = "user@example.com", password: str = "secret123") -> User:
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        is_confirmed=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_update_user_profile_updates_full_name(db_session: Session) -> None:
    user = _create_user(db_session)

    update_user_profile(db_session, user, UserProfileUpdate(full_name="New Name"))
    db_session.refresh(user)

    assert user.full_name == "New Name"


def test_update_user_profile_email_change_triggers_confirmation(
    db_session: Session,
    capture_outbound_email: list[dict[str, str]],
) -> None:
    user = _create_user(db_session)
    user.confirmed_at = datetime.now(timezone.utc)
    user.is_confirmed = True
    db_session.commit()

    update_user_profile(
        db_session,
        user,
        UserProfileUpdate(email="new@example.com"),
    )
    db_session.refresh(user)

    assert user.email == "new@example.com"
    assert user.is_confirmed is False
    assert user.confirmed_at is None
    assert capture_outbound_email
    assert capture_outbound_email[-1]["recipient"] == "new@example.com"


def test_update_user_profile_background_tasks_queue_email(
    db_session: Session,
    capture_outbound_email: list[dict[str, str]],
) -> None:
    user = _create_user(db_session)
    background_tasks = BackgroundTasks()

    update_user_profile(
        db_session,
        user,
        UserProfileUpdate(email="queued@example.com"),
        background_tasks=background_tasks,
    )

    assert len(background_tasks.tasks) == 1
    assert not capture_outbound_email

    for task in background_tasks.tasks:
        task.func(*task.args, **task.kwargs)

    assert capture_outbound_email[-1]["recipient"] == "queued@example.com"


def test_update_user_profile_duplicate_email_guard(db_session: Session) -> None:
    _create_user(db_session, email="primary@example.com")
    other = _create_user(db_session, email="secondary@example.com")

    with pytest.raises(UserEmailAlreadyExistsError):
        update_user_profile(db_session, other, UserProfileUpdate(email="primary@example.com"))


def test_change_user_password_success(db_session: Session) -> None:
    user = _create_user(db_session)

    change_user_password(
        db_session,
        user,
        PasswordChangeRequest(current_password="secret123", new_password="newsecret1"),
    )
    db_session.refresh(user)

    assert verify_password("newsecret1", user.hashed_password)


def test_change_user_password_incorrect_current(db_session: Session) -> None:
    user = _create_user(db_session)

    with pytest.raises(IncorrectPasswordError):
        change_user_password(
            db_session,
            user,
            PasswordChangeRequest(current_password="wrongpass", new_password="newsecret1"),
        )


def test_link_login_provider_and_prevent_duplicates(db_session: Session) -> None:
    user = _create_user(db_session)

    link_login_provider(db_session, user, "google", "google-123")
    db_session.refresh(user)
    assert user.google_oauth_sub == "google-123"

    with pytest.raises(LoginProviderAlreadyLinkedError):
        link_login_provider(db_session, user, "google", "other")


def test_unlink_login_provider_flow(db_session: Session) -> None:
    user = _create_user(db_session)
    link_login_provider(db_session, user, "github", "octocat")

    unlink_login_provider(db_session, user, "github")
    db_session.refresh(user)
    assert user.github_oauth_id is None

    with pytest.raises(LoginProviderNotLinkedError):
        unlink_login_provider(db_session, user, "github")


def test_unlink_login_provider_blocks_last_method(db_session: Session) -> None:
    user = User(
        email="oauth@example.com",
        hashed_password="",
        google_oauth_sub="oauth-id",
        is_confirmed=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    with pytest.raises(LastLoginMethodRemovalError):
        unlink_login_provider(db_session, user, "google")
