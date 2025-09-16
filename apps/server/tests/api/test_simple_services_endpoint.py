"""Tests for the simplified services endpoint."""

from __future__ import annotations

from tests.conftest import SyncASGITestClient


def test_simple_services_endpoint_returns_services(
    client: SyncASGITestClient, auth_token: str
) -> None:
    """Endpoint returns the list of available services."""

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/api/v1/services/services", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "services" in data
    assert isinstance(data["services"], list)
    assert len(data["services"]) > 0

    for service in data["services"]:
        assert "slug" in service
        assert "name" in service
        assert "description" in service
        assert "actions" not in service
        assert "reactions" not in service


def test_simple_services_endpoint_v1_returns_services(
    client: SyncASGITestClient, auth_token: str
) -> None:
    """Endpoint returns the list of available services via legacy prefix."""

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/services/services", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "services" in data
    assert isinstance(data["services"], list)
    assert len(data["services"]) > 0

    for service in data["services"]:
        assert "slug" in service
        assert "name" in service
        assert "description" in service
        assert "actions" not in service
        assert "reactions" not in service

