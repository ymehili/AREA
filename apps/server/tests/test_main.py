import asyncio

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture()
def client():
    with TestClient(main.app) as client:
        yield client


def test_startup_event_sets_database_url(verify_connection_tracker):
    main.app.state.database_url = None
    asyncio.run(main.startup_event())
    assert verify_connection_tracker["calls"] == 1
    assert main.app.state.database_url == main.settings.database_url


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Server is running"}


def test_about_endpoint_includes_catalog(client):
    response = client.get("/about.json")
    assert response.status_code == 200
    payload = response.json()
    assert payload["client"]
    assert payload["server"]["current_time"]
    assert isinstance(payload["services"], list)
    assert payload["services"], "catalog should not be empty"


def test_list_service_actions_reactions(client):
    response = client.get("/services/actions-reactions")
    assert response.status_code == 200
    payload = response.json()
    assert "services" in payload
    assert all("actions" in service for service in payload["services"])
    assert all("reactions" in service for service in payload["services"])
