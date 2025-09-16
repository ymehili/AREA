"""Regression tests covering the public service catalog endpoints."""

from __future__ import annotations

from app.integrations.catalog import service_catalog_payload
from tests.conftest import SyncASGITestClient


def test_about_includes_service_catalog(client: SyncASGITestClient) -> None:
    response = client.get("/about.json")
    assert response.status_code == 200
    about = response.json()
    assert about["services"] == service_catalog_payload()


def test_actions_reactions_endpoint_matches_catalog(
    client: SyncASGITestClient, auth_token: str
) -> None:
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/api/v1/services/actions-reactions", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload == {"services": service_catalog_payload()}

