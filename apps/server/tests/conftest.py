import pytest

import main


@pytest.fixture(autouse=True)
def verify_connection_tracker(monkeypatch):
    tracker = {"calls": 0}

    def fake_verify_connection():
        tracker["calls"] += 1

    monkeypatch.setattr(main, "verify_connection", fake_verify_connection)
    yield tracker
