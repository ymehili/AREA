"""Tests for the simplified services endpoint."""

import pytest
from fastapi.testclient import TestClient

from main import app


def _create_test_client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def client() -> TestClient:
    return _create_test_client()


def test_simple_services_endpoint_returns_services(client: TestClient) -> None:
    """Endpoint returns the list of available services."""
    response = client.get("/api/v1/services/services")
    assert response.status_code == 200
    data = response.json()
    assert "services" in data
    assert isinstance(data["services"], list)
    assert len(data["services"]) > 0
    
    # Check that each service has the required fields
    for service in data["services"]:
        assert "slug" in service
        assert "name" in service
        assert "description" in service
        # Ensure actions and reactions are not included
        assert "actions" not in service
        assert "reactions" not in service


def test_simple_services_endpoint_v1_returns_services(client: TestClient) -> None:
    """Endpoint returns the list of available services."""
    response = client.get("/services/services")
    assert response.status_code == 200
    data = response.json()
    assert "services" in data
    assert isinstance(data["services"], list)
    assert len(data["services"]) > 0
    
    # Check that each service has the required fields
    for service in data["services"]:
        assert "slug" in service
        assert "name" in service
        assert "description" in service
        # Ensure actions and reactions are not included
        assert "actions" not in service
        assert "reactions" not in service