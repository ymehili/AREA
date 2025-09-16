"""Tests for service catalog exposure endpoints."""

from __future__ import annotations

from inspect import signature

import httpx
import pytest
from fastapi.testclient import TestClient

from app.integrations.catalog import service_catalog_payload
from main import app


def _create_test_client() -> TestClient:
    """Instantiate a TestClient compatible with the bundled httpx version."""

    if "app" not in signature(httpx.Client.__init__).parameters:
        original_init = httpx.Client.__init__

        def patched_init(self, *args, **kwargs):
            kwargs.pop("app", None)
            return original_init(self, *args, **kwargs)

        httpx.Client.__init__ = patched_init

    return TestClient(app)


@pytest.fixture()
def client() -> TestClient:
    """Provide a configured TestClient instance."""

    return _create_test_client()


def test_about_includes_service_catalog(client: TestClient) -> None:
    """/about.json responds with the service catalog payload."""

    response = client.get("/about.json")
    assert response.status_code == 200
    about = response.json()
    assert about["services"] == service_catalog_payload()


def test_actions_reactions_endpoint_matches_catalog(client: TestClient) -> None:
    """Endpoint returns the same catalog structure as the about page."""

    response = client.get("/api/v1/services/actions-reactions")
    assert response.status_code == 200
    assert response.json() == {"services": service_catalog_payload()}
