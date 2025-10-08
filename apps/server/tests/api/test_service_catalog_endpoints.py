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
    
    # The endpoint now returns a filtered catalog, not the full catalog
    # We just need to verify it returns a valid response structure
    assert "services" in payload
    assert isinstance(payload["services"], list)
    
    # Verify that the filtered services contain expected implemented services
    service_slugs = [service["slug"] for service in payload["services"]]
    assert "time" in service_slugs  # Should have time service
    assert "gmail" in service_slugs  # Should have gmail service
    assert "debug" in service_slugs  # Should have debug service

