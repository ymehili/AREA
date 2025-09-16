"""Tests covering authentication API endpoints."""

from __future__ import annotations

import uuid

from jose import jwt

from app.core.config import settings
from tests.conftest import SyncASGITestClient


def test_register_creates_user(client: SyncASGITestClient) -> None:
    payload = {"email": "new-user@example.com", "password": "password123"}
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert uuid.UUID(data["id"])  # ensure valid UUID
    assert "hashed_password" not in data


def test_register_duplicate_email_returns_400(client: SyncASGITestClient) -> None:
    payload = {"email": "duplicate@example.com", "password": "password123"}
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201
    second = client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 400
    assert second.json()["detail"]


def test_login_returns_token(client: SyncASGITestClient) -> None:
    credentials = {"email": "login@example.com", "password": "password123"}
    client.post("/api/v1/auth/register", json=credentials)
    response = client.post("/api/v1/auth/login", json=credentials)
    assert response.status_code == 200
    token_payload = response.json()
    assert token_payload["token_type"] == "bearer"
    decoded = jwt.decode(
        token_payload["access_token"],
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    assert decoded["sub"]


def test_login_rejects_bad_password(client: SyncASGITestClient) -> None:
    credentials = {"email": "badpass@example.com", "password": "password123"}
    client.post("/api/v1/auth/register", json=credentials)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": credentials["email"], "password": "wrongpass"},
    )
    assert response.status_code == 401


def test_login_rejects_unknown_user(client: SyncASGITestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "password123"},
    )
    assert response.status_code == 401


def test_token_contains_uuid_subject(client: SyncASGITestClient) -> None:
    credentials = {"email": "uuid@example.com", "password": "password123"}
    client.post("/api/v1/auth/register", json=credentials)
    response = client.post("/api/v1/auth/login", json=credentials)
    token_payload = response.json()
    claims = jwt.decode(
        token_payload["access_token"],
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    assert uuid.UUID(claims["sub"])  # raises if not valid UUID

