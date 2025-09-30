"""Shared pytest fixtures for server tests."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Generator
from datetime import datetime, timezone
import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

def _ensure_test_encryption_key() -> None:
    """Guarantee a valid Fernet key for the test environment."""

    current = os.environ.get("ENCRYPTION_KEY")
    if current:
        try:
            Fernet(current.encode() if isinstance(current, str) else current)
            return
        except ValueError:
            pass

    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()


_ensure_test_encryption_key()

import main
from app.db.base import Base
from app.db.session import get_db
from app.models import area as area_model  # noqa: F401 - ensure model registration
from app.models import area_step as area_step_model  # noqa: F401 - ensure model registration
from app.models import email_verification_token as email_token_model  # noqa: F401 - ensure model registration
from app.models import service_connection as service_connection_model  # noqa: F401 - ensure model registration
from app.models import user as user_model  # noqa: F401 - ensure model registration
from app.services import get_user_by_email


@compiles(UUID, "sqlite")
def compile_uuid_sqlite(_element, _compiler, **_kw) -> str:
    """Render UUID columns as TEXT for the SQLite test database."""

    return "TEXT"


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(_element, _compiler, **_kw) -> str:
    """Render JSONB columns as TEXT for the SQLite test database."""

    return "TEXT"


TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    future=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
    future=True,
)

Base.metadata.create_all(bind=test_engine)


class SyncASGITestClient:
    """Synchronous wrapper around httpx.AsyncClient for ASGI apps."""

    def __init__(self, app) -> None:
        transport = httpx.ASGITransport(app=app)
        self._client = httpx.AsyncClient(transport=transport, base_url="http://testserver")

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        return asyncio.run(self._client.request(method, url, **kwargs))

    def get(self, url: str, **kwargs) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def delete(self, url: str, **kwargs) -> httpx.Response:
        return self.request("DELETE", url, **kwargs)

    def put(self, url: str, **kwargs) -> httpx.Response:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs) -> httpx.Response:
        return self.request("PATCH", url, **kwargs)

    def __enter__(self) -> "SyncASGITestClient":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        asyncio.run(self._client.aclose())


@pytest.fixture(autouse=True)
def verify_connection_tracker(monkeypatch: pytest.MonkeyPatch) -> Generator[dict[str, int], None, None]:
    """Track how many times the startup connection verifier is called."""

    tracker = {"calls": 0, "migrations": 0}

    def fake_verify_connection() -> None:
        tracker["calls"] += 1

    def fake_run_migrations() -> None:
        tracker["migrations"] += 1

    monkeypatch.setattr(main, "verify_connection", fake_verify_connection)
    monkeypatch.setattr(main, "run_migrations", fake_run_migrations)
    yield tracker


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """Provide a clean database session for each test."""

    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session: Session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def override_get_db(db_session: Session) -> Generator[None, None, None]:
    """Override the FastAPI dependency to use the test session."""

    def _get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    main.app.dependency_overrides[get_db] = _get_db
    yield
    main.app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def client() -> Generator[SyncASGITestClient, None, None]:
    """Synchronous test client backed by httpx's ASGI transport."""

    with SyncASGITestClient(main.app) as test_client:
        yield test_client


@pytest.fixture()
def user_credentials() -> dict[str, str]:
    """Default credentials used to register/login test users."""

    return {"email": "user@example.com", "password": "secret123"}


@pytest.fixture(autouse=True)
def capture_outbound_email(monkeypatch: pytest.MonkeyPatch) -> Generator[list[dict[str, str]], None, None]:
    """Record outbound confirmation emails for assertions."""

    sent: list[dict[str, str]] = []

    def _capture(recipient: str, link: str) -> None:
        sent.append({"recipient": recipient, "link": link})

    monkeypatch.setattr("app.services.email.send_confirmation_email", _capture)
    monkeypatch.setattr("app.services.users.send_confirmation_email", _capture)
    monkeypatch.setattr("app.services.send_confirmation_email", _capture)
    monkeypatch.setattr("app.api.routes.auth.send_confirmation_email", _capture)
    yield sent


@pytest.fixture()
def auth_token(
    client: SyncASGITestClient,
    db_session: Session,
    user_credentials: dict[str, str],
) -> str:
    """Create and confirm a user, returning an authentication token."""

    register_response = client.post("/api/v1/auth/register", json=user_credentials)
    assert register_response.status_code == 201

    user = get_user_by_email(db_session, user_credentials["email"])
    assert user is not None
    user.is_confirmed = True
    user.confirmed_at = datetime.now(timezone.utc)
    db_session.commit()

    login_response = client.post("/api/v1/auth/login", json=user_credentials)
    assert login_response.status_code == 200
    token_data = login_response.json()
    return token_data["access_token"]
