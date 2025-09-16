from types import SimpleNamespace

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.db import session


def test_get_db_yields_session_and_closes(monkeypatch):
    closed = False

    class DummySession:
        def close(self):
            nonlocal closed
            closed = True

    monkeypatch.setattr(session, "SessionLocal", lambda: DummySession())

    generator = session.get_db()
    produced_session = next(generator)
    assert isinstance(produced_session, DummySession)

    with pytest.raises(StopIteration):
        next(generator)

    assert closed, "Session should be closed after generator exits"


def test_verify_connection_executes_health_query(monkeypatch):
    executed = SimpleNamespace(value=False)

    class DummyConnection:
        def execute(self, statement):
            executed.value = True
            assert "SELECT 1" in str(statement)

    class DummyConnectionManager:
        def __enter__(self):
            return DummyConnection()

        def __exit__(self, *exc):
            return False

    class DummyEngine:
        def connect(self):
            return DummyConnectionManager()

    monkeypatch.setattr(session, "engine", DummyEngine())

    session.verify_connection()
    assert executed.value


def test_verify_connection_propagates_sqlalchemy_errors(monkeypatch):
    class DummyEngine:
        def connect(self):
            raise SQLAlchemyError("boom")

    monkeypatch.setattr(session, "engine", DummyEngine())

    with pytest.raises(SQLAlchemyError):
        session.verify_connection()
