import asyncio

import main
from tests.conftest import SyncASGITestClient


def test_startup_event_sets_database_url(verify_connection_tracker):
    main.app.state.database_url = None
    asyncio.run(main.startup_event())
    assert verify_connection_tracker["calls"] == 1
    # Migrations now run before app creation, not in startup event
    assert main.app.state.database_url == main.settings.database_url


def test_root_endpoint(client: SyncASGITestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Server is running"}


def test_about_endpoint_includes_catalog(client: SyncASGITestClient):
    response = client.get("/about.json")
    assert response.status_code == 200
    payload = response.json()
    assert payload["client"]
    assert payload["server"]["current_time"]
    assert isinstance(payload["services"], list)
    assert payload["services"], "catalog should not be empty"


def test_list_service_actions_reactions(client: SyncASGITestClient, auth_token: str):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/services/actions-reactions", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert "services" in payload
    assert all("actions" in service for service in payload["services"])
    assert all("reactions" in service for service in payload["services"])
