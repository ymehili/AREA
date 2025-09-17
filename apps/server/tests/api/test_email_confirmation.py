"""Tests covering the email confirmation flow endpoints."""

from __future__ import annotations

from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from app.core.config import settings
from app.services import get_user_by_email
from tests.conftest import SyncASGITestClient


def _extract_token(capture_outbound_email) -> str:
    assert capture_outbound_email, "Expected an outbound confirmation email"
    link = capture_outbound_email[-1]["link"]
    parsed = urlparse(link)
    token = parse_qs(parsed.query).get("token", [None])[0]
    assert token is not None
    return token


def test_resend_confirmation_sends_email(
    client: SyncASGITestClient,
    capture_outbound_email,
) -> None:
    payload = {"email": "resend@example.com", "password": "password123"}
    client.post("/api/v1/auth/register", json=payload)
    capture_outbound_email.clear()

    response = client.post("/api/v1/auth/resend-confirmation", json={"email": payload["email"]})
    assert response.status_code == 202
    assert capture_outbound_email


def test_resend_confirmation_blocks_confirmed_account(
    client: SyncASGITestClient,
    db_session,
    capture_outbound_email,
) -> None:
    payload = {"email": "confirmed@example.com", "password": "password123"}
    client.post("/api/v1/auth/register", json=payload)
    user = get_user_by_email(db_session, payload["email"])
    assert user is not None
    user.is_confirmed = True
    db_session.commit()

    response = client.post("/api/v1/auth/resend-confirmation", json={"email": payload["email"]})
    assert response.status_code == 400


def test_confirm_email_redirects_to_success(
    client: SyncASGITestClient,
    db_session,
    capture_outbound_email,
) -> None:
    payload = {"email": "confirm@example.com", "password": "password123"}
    client.post("/api/v1/auth/register", json=payload)
    token = _extract_token(capture_outbound_email)

    response = client.get(f"/api/v1/auth/confirm?token={token}", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == settings.email_confirmation_success_redirect_url

    user = get_user_by_email(db_session, payload["email"])
    assert user is not None and user.is_confirmed


def test_confirm_email_redirects_to_failure_for_invalid_token(
    client: SyncASGITestClient,
) -> None:
    response = client.get("/api/v1/auth/confirm?token=invalid", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == settings.email_confirmation_failure_redirect_url


def test_confirm_email_redirects_to_failure_for_expired_token(
    client: SyncASGITestClient,
    db_session,
    capture_outbound_email,
) -> None:
    payload = {"email": "expired@example.com", "password": "password123"}
    client.post("/api/v1/auth/register", json=payload)
    token = _extract_token(capture_outbound_email)

    user = get_user_by_email(db_session, payload["email"])
    assert user is not None
    token_record = user.email_verification_tokens[-1]
    token_record.expires_at = token_record.expires_at - timedelta(days=1)
    db_session.commit()

    response = client.get(f"/api/v1/auth/confirm?token={token}", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == settings.email_confirmation_failure_redirect_url


def test_confirm_email_duplicate_use_is_idempotent(
    client: SyncASGITestClient,
    capture_outbound_email,
) -> None:
    payload = {"email": "duplicate@example.com", "password": "password123"}
    client.post("/api/v1/auth/register", json=payload)
    token = _extract_token(capture_outbound_email)

    first = client.get(f"/api/v1/auth/confirm?token={token}", follow_redirects=False)
    assert first.status_code == 303

    second = client.get(f"/api/v1/auth/confirm?token={token}", follow_redirects=False)
    assert second.status_code == 303
    assert second.headers["location"] == settings.email_confirmation_success_redirect_url
