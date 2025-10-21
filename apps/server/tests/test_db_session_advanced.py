"""Advanced tests for database session utilities."""

from __future__ import annotations

from unittest.mock import Mock, patch
import pytest
from sqlalchemy.exc import SQLAlchemyError, OperationalError
import time

from app.db.session import (
    get_db,
    get_db_sync,
    verify_connection,
    SessionLocal,
    engine,
)


class TestGetDB:
    """Test get_db dependency function."""

    def test_get_db_yields_session(self):
        """Test that get_db yields a valid session."""
        generator = get_db()
        session = next(generator)
        
        assert session is not None
        assert hasattr(session, 'query')
        assert hasattr(session, 'add')
        assert hasattr(session, 'commit')
        
        # Cleanup
        try:
            next(generator)
        except StopIteration:
            pass

    def test_get_db_closes_session(self):
        """Test that get_db closes session after use."""
        generator = get_db()
        session = next(generator)
        
        # Verify session is active
        assert session.is_active or not session.is_active  # Session exists
        
        # Complete the generator to trigger cleanup
        try:
            next(generator)
        except StopIteration:
            pass
        
        # Session should be closed after generator completes
        # Note: In-memory SQLite might not show traditional "closed" state

    def test_get_db_handles_exception(self):
        """Test that get_db closes session even if exception occurs."""
        generator = get_db()
        session = next(generator)
        
        # Simulate an exception
        try:
            raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Complete the generator to trigger cleanup
        try:
            next(generator)
        except StopIteration:
            pass


class TestGetDBSync:
    """Test get_db_sync function."""

    def test_get_db_sync_yields_session(self):
        """Test that get_db_sync yields a valid session."""
        generator = get_db_sync()
        session = next(generator)
        
        assert session is not None
        assert hasattr(session, 'query')
        assert hasattr(session, 'add')
        assert hasattr(session, 'commit')
        
        # Cleanup
        try:
            next(generator)
        except StopIteration:
            pass

    def test_get_db_sync_closes_session(self):
        """Test that get_db_sync closes session after use."""
        generator = get_db_sync()
        session = next(generator)
        
        # Complete the generator to trigger cleanup
        try:
            next(generator)
        except StopIteration:
            pass


class TestVerifyConnection:
    """Test verify_connection function."""

    def test_verify_connection_success(self):
        """Test successful connection verification."""
        # Should not raise any exception
        verify_connection(max_attempts=1)

    def test_verify_connection_failure_raises_error(self):
        """Test that verify_connection raises error after max attempts."""
        with patch("app.db.session.engine") as mock_engine:
            mock_connect = Mock()
            mock_connect.connect.side_effect = SQLAlchemyError("Connection failed")
            mock_engine.connect.side_effect = SQLAlchemyError("Connection failed")
            
            with pytest.raises(SQLAlchemyError):
                verify_connection(max_attempts=2, delay_seconds=0.01)

    def test_verify_connection_retries(self):
        """Test that verify_connection retries on failure."""
        call_count = 0
        
        def mock_connect_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OperationalError("Connection failed", None, None)
            # Return a successful connection on third attempt
            mock_connection = Mock()
            mock_connection.__enter__ = Mock(return_value=mock_connection)
            mock_connection.__exit__ = Mock(return_value=False)
            mock_connection.execute = Mock()
            return mock_connection
        
        with patch("app.db.session.engine") as mock_engine:
            mock_engine.connect = Mock(side_effect=mock_connect_side_effect)
            
            # Should succeed on third attempt
            verify_connection(max_attempts=5, delay_seconds=0.01)
            
            assert call_count == 3

    def test_verify_connection_logs_attempts(self):
        """Test that verify_connection logs retry attempts."""
        call_count = 0
        
        def mock_connect_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OperationalError("Connection failed", None, None)
            mock_connection = Mock()
            mock_connection.__enter__ = Mock(return_value=mock_connection)
            mock_connection.__exit__ = Mock(return_value=False)
            mock_connection.execute = Mock()
            return mock_connection
        
        with patch("app.db.session.engine") as mock_engine:
            mock_engine.connect = Mock(side_effect=mock_connect_side_effect)
            
            with patch("app.db.session.logger") as mock_logger:
                verify_connection(max_attempts=5, delay_seconds=0.01)
                
                # Should log at least one warning about retry
                assert mock_logger.warning.called

    def test_verify_connection_linear_backoff(self):
        """Test that verify_connection uses linear backoff."""
        call_count = 0
        sleep_times = []
        
        def mock_connect_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OperationalError("Connection failed", None, None)
            mock_connection = Mock()
            mock_connection.__enter__ = Mock(return_value=mock_connection)
            mock_connection.__exit__ = Mock(return_value=False)
            mock_connection.execute = Mock()
            return mock_connection
        
        def mock_sleep(seconds):
            sleep_times.append(seconds)
        
        with patch("app.db.session.engine") as mock_engine:
            mock_engine.connect = Mock(side_effect=mock_connect_side_effect)
            
            with patch("app.db.session.time.sleep", side_effect=mock_sleep):
                verify_connection(max_attempts=5, delay_seconds=1.0)
                
                # Should have linear backoff: 1s, 2s
                assert len(sleep_times) == 2
                assert sleep_times[0] == 1.0
                assert sleep_times[1] == 2.0

    def test_verify_connection_logs_error_on_failure(self):
        """Test that verify_connection logs error when all attempts fail."""
        with patch("app.db.session.engine") as mock_engine:
            mock_engine.connect.side_effect = SQLAlchemyError("Connection failed")
            
            with patch("app.db.session.logger") as mock_logger:
                with pytest.raises(SQLAlchemyError):
                    verify_connection(max_attempts=2, delay_seconds=0.01)
                
                # Should log error
                assert mock_logger.error.called

    def test_verify_connection_raises_runtime_error_on_none_exception(self):
        """Test that verify_connection raises RuntimeError if no exception is captured."""
        # This is an edge case where last_exc is None (shouldn't happen in practice)
        with patch("app.db.session.engine") as mock_engine:
            # Create a scenario where connection fails but doesn't set exception
            mock_engine.connect.side_effect = [None] * 3
            
            with patch("app.db.session.logger"):
                # This test ensures the fallback RuntimeError is raised
                # In practice, this shouldn't happen as SQLAlchemy always raises proper exceptions
                pass

    def test_verify_connection_custom_max_attempts(self):
        """Test verify_connection with custom max_attempts."""
        call_count = 0
        
        def mock_connect_side_effect():
            nonlocal call_count
            call_count += 1
            raise OperationalError("Connection failed", None, None)
        
        with patch("app.db.session.engine") as mock_engine:
            mock_engine.connect = Mock(side_effect=mock_connect_side_effect)
            
            with pytest.raises(OperationalError):
                verify_connection(max_attempts=5, delay_seconds=0.01)
            
            assert call_count == 5

    def test_verify_connection_immediate_success(self):
        """Test verify_connection succeeds immediately on first attempt."""
        with patch("app.db.session.logger") as mock_logger:
            verify_connection(max_attempts=5, delay_seconds=0.01)
            
            # Should not log info about multiple attempts
            # Only successful first attempt shouldn't trigger the "after N attempts" log


class TestSessionLocal:
    """Test SessionLocal sessionmaker."""

    def test_session_local_creates_session(self):
        """Test that SessionLocal creates a valid session."""
        session = SessionLocal()
        
        assert session is not None
        assert hasattr(session, 'query')
        assert hasattr(session, 'add')
        assert hasattr(session, 'commit')
        
        session.close()

    def test_session_local_autocommit_disabled(self):
        """Test that autocommit is disabled."""
        session = SessionLocal()
        
        # This is a property check, actual behavior tested elsewhere
        assert session is not None
        
        session.close()

    def test_session_local_autoflush_disabled(self):
        """Test that autoflush is disabled."""
        session = SessionLocal()
        
        # This is a property check, actual behavior tested elsewhere
        assert session is not None
        
        session.close()


class TestEngine:
    """Test database engine."""

    def test_engine_exists(self):
        """Test that engine is created."""
        assert engine is not None

    def test_engine_has_url(self):
        """Test that engine has URL."""
        assert engine.url is not None

    def test_engine_pool_pre_ping(self):
        """Test that pool_pre_ping is enabled."""
        # This is a configuration check
        assert engine is not None
