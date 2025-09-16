"""Regression tests covering the public service catalog endpoints."""

from fastapi.testclient import TestClient

from app.integrations.catalog import service_catalog_payload
from main import app


def test_about_includes_service_catalog():
    with TestClient(app) as client:
        response = client.get("/about.json")
        assert response.status_code == 200
        about = response.json()
    assert about["services"] == service_catalog_payload()


def test_actions_reactions_endpoint_matches_catalog():
    with TestClient(app) as client:
        response = client.get("/api/v1/services/actions-reactions")
        assert response.status_code == 200
        payload = response.json()
    assert payload == {"services": service_catalog_payload()}
