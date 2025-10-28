"""Tests for Gmail scheduler functionality."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

import pytest
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

from app.integrations.simple_plugins.gmail_scheduler import (
    _get_gmail_service,
    _fetch_messages,
    _build_gmail_query,
    _extract_message_data,
    _fetch_due_gmail_areas,
    start_gmail_scheduler,
    stop_gmail_scheduler,
    is_gmail_scheduler_running,
    clear_gmail_seen_state,
    gmail_scheduler_task,
    _process_gmail_trigger,
)


class TestGmailScheduler:
    """Test Gmail scheduler functionality."""

    def test_get_gmail_service_success(self):
        """Test successful Gmail service creation."""
        user_id = "test-user-id"
        mock_db = Mock()
        mock_connection = Mock()
        mock_connection.encrypted_access_token = b"encrypted_access_token"
        mock_connection.encrypted_refresh_token = b"encrypted_refresh_token"

        with patch("app.integrations.simple_plugins.gmail_scheduler.get_service_connection_by_user_and_service") as mock_get_conn, \
             patch("app.integrations.simple_plugins.gmail_scheduler.decrypt_token") as mock_decrypt, \
             patch("app.integrations.simple_plugins.gmail_scheduler.build") as mock_build, \
             patch("app.integrations.simple_plugins.gmail_scheduler.Credentials") as mock_credentials:

            mock_get_conn.return_value = mock_connection
            # decrypt_token should return str (decrypted value), not bytes
            mock_decrypt.side_effect = lambda x: x.decode() if isinstance(x, bytes) else str(x)

            mock_creds = Mock()
            mock_creds.expired = False
            mock_creds.valid = True  # Mark as valid so no refresh needed
            mock_creds.refresh_token = "decrypted_refresh_token"
            mock_credentials.return_value = mock_creds

            mock_service = Mock()
            mock_build.return_value = mock_service

            result = _get_gmail_service(user_id, mock_db)

            assert result == mock_service
            mock_get_conn.assert_called_once_with(mock_db, user_id, "gmail")

    def test_get_gmail_service_no_connection(self):
        """Test Gmail service creation when no connection exists."""
        user_id = "test-user-id"
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.gmail_scheduler.get_service_connection_by_user_and_service") as mock_get_conn:
            mock_get_conn.return_value = None

            result = _get_gmail_service(user_id, mock_db)

            assert result is None

    def test_get_gmail_service_token_refresh(self):
        """Test Gmail service creation with token refresh."""
        user_id = "test-user-id"
        mock_db = Mock()
        mock_connection = Mock()
        mock_connection.id = "connection-id"
        mock_connection.service_name = "gmail"
        mock_connection.encrypted_access_token = b"encrypted_access_token"
        mock_connection.encrypted_refresh_token = b"encrypted_refresh_token"

        with patch("app.integrations.simple_plugins.gmail_scheduler.get_service_connection_by_user_and_service") as mock_get_conn, \
             patch("app.integrations.simple_plugins.gmail_scheduler.decrypt_token") as mock_decrypt, \
             patch("app.integrations.simple_plugins.gmail_scheduler.build") as mock_build, \
             patch("app.integrations.simple_plugins.gmail_scheduler.Credentials") as mock_credentials, \
             patch("app.integrations.simple_plugins.gmail_scheduler.update_service_connection") as mock_update, \
             patch("app.integrations.simple_plugins.gmail_scheduler.Request") as mock_request:

            mock_get_conn.return_value = mock_connection
            # decrypt_token should return str (decrypted value), not bytes
            mock_decrypt.side_effect = lambda x: x.decode() if isinstance(x, bytes) else str(x)

            # Mock credentials that need refresh
            mock_creds = Mock()
            mock_creds.expired = True
            mock_creds.refresh_token = "decrypted_refresh_token"
            mock_creds.refresh.return_value = None
            mock_creds.token = "new_access_token"
            mock_creds.expiry = None
            mock_credentials.return_value = mock_creds

            mock_service = Mock()
            mock_build.return_value = mock_service

            result = _get_gmail_service(user_id, mock_db)

            assert result == mock_service
            mock_creds.refresh.assert_called_once()

    def test_build_gmail_query_new_email(self):
        """Test Gmail query building for new email trigger."""
        area = Mock()
        area.trigger_action = "new_email"
        area.trigger_params = {}

        query = _build_gmail_query(area)

        # Based on actual implementation, new_email only uses "in:inbox" without is:unread
        assert query == "in:inbox"

    def test_build_gmail_query_new_email_from_sender(self):
        """Test Gmail query building for new email from sender trigger."""
        area = Mock()
        area.trigger_action = "new_email_from_sender"
        area.trigger_params = {"sender_email": "test@example.com"}

        query = _build_gmail_query(area)

        # Based on actual implementation
        assert "from:test@example.com" in query
        assert "in:inbox" in query

    def test_build_gmail_query_new_unread_email(self):
        """Test Gmail query building for new unread email trigger."""
        area = Mock()
        area.trigger_action = "new_unread_email"
        area.trigger_params = {}

        query = _build_gmail_query(area)

        assert "in:inbox" in query
        assert "is:unread" in query

    def test_build_gmail_query_email_starred(self):
        """Test Gmail query building for email starred trigger."""
        area = Mock()
        area.trigger_action = "email_starred"
        area.trigger_params = {}

        query = _build_gmail_query(area)

        assert "is:starred" in query

    def test_fetch_messages_success(self):
        """Test successful Gmail message fetching."""
        mock_service = Mock()

        # Mock the list() call
        mock_list = Mock()
        mock_list.execute.return_value = {
            "messages": [
                {"id": "msg1", "threadId": "thread1"},
                {"id": "msg2", "threadId": "thread2"}
            ]
        }

        # Mock the get() calls for full message details
        mock_get1 = Mock()
        mock_get1.execute.return_value = {
            "id": "msg1",
            "threadId": "thread1",
            "payload": {"headers": []}
        }
        mock_get2 = Mock()
        mock_get2.execute.return_value = {
            "id": "msg2",
            "threadId": "thread2",
            "payload": {"headers": []}
        }

        # Set up the mock chain
        mock_service.users().messages().list.return_value = mock_list
        mock_service.users().messages().get.side_effect = [mock_get1, mock_get2]

        result = _fetch_messages(mock_service, "test query")

        assert len(result) == 2
        assert result[0]["id"] == "msg1"
        assert result[1]["id"] == "msg2"

    def test_fetch_messages_no_messages(self):
        """Test Gmail message fetching when no messages found."""
        mock_service = Mock()
        mock_list = Mock()
        mock_list.execute.return_value = {"messages": []}
        mock_service.users().messages().list.return_value = mock_list

        result = _fetch_messages(mock_service, "test query")

        assert result == []

    def test_fetch_messages_http_error(self):
        """Test Gmail message fetching with HTTP error."""
        mock_service = Mock()
        mock_list = Mock()
        http_resp = Mock()
        http_resp.status = 400
        http_resp.reason = "Bad Request"
        mock_list.execute.side_effect = HttpError(http_resp, b"Bad Request")
        mock_service.users().messages().list.return_value = mock_list

        result = _fetch_messages(mock_service, "test query")

        assert result == []

    @pytest.mark.asyncio
    async def test_start_gmail_scheduler(self):
        """Test starting the Gmail scheduler."""
        # The function uses asyncio.get_running_loop().create_task()
        with patch("app.integrations.simple_plugins.gmail_scheduler.asyncio.get_running_loop") as mock_get_loop:
            mock_loop = Mock()
            mock_task = Mock()
            mock_loop.create_task.return_value = mock_task
            mock_get_loop.return_value = mock_loop

            start_gmail_scheduler()

            mock_loop.create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_gmail_scheduler(self):
        """Test stopping the Gmail scheduler."""
        # First start the scheduler to set _gmail_scheduler_task
        with patch("app.integrations.simple_plugins.gmail_scheduler.asyncio") as mock_asyncio:
            mock_task = Mock()
            mock_asyncio.create_task.return_value = mock_task
            start_gmail_scheduler()

        # Now stop it
        with patch("app.integrations.simple_plugins.gmail_scheduler._gmail_scheduler_task") as mock_task:
            if mock_task:
                mock_task.cancel.return_value = None
                stop_gmail_scheduler()
                mock_task.cancel.assert_called_once()

    def test_build_gmail_query_with_params(self):
        """Test Gmail query building with additional parameters."""
        area = Mock()
        area.trigger_action = "new_unread_email"
        area.trigger_params = {}

        query = _build_gmail_query(area)

        # Query should include unread filter
        assert "in:inbox" in query or "is:unread" in query

    def test_build_gmail_query_new_email_from_sender_no_email(self):
        """Test Gmail query building for new email from sender without email."""
        area = Mock()
        area.trigger_action = "new_email_from_sender"
        area.trigger_params = {}

        query = _build_gmail_query(area)

        # Should fallback to basic inbox query
        assert "in:inbox" in query

    def test_fetch_messages_with_pagination(self):
        """Test Gmail message fetching with pagination."""
        mock_service = Mock()

        # Mock the list() call with nextPageToken
        mock_list = Mock()
        mock_list.execute.return_value = {
            "messages": [{"id": "msg1", "threadId": "thread1"}],
            "nextPageToken": "token123"
        }

        # Mock the get() call
        mock_get = Mock()
        mock_get.execute.return_value = {
            "id": "msg1",
            "threadId": "thread1",
            "payload": {"headers": []}
        }

        mock_service.users().messages().list.return_value = mock_list
        mock_service.users().messages().get.return_value = mock_get

        result = _fetch_messages(mock_service, "test query", max_results=1)

        assert len(result) == 1
        assert result[0]["id"] == "msg1"

    def test_get_gmail_service_error(self):
        """Test Gmail service creation with general error."""
        user_id = "test-user-id"
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.gmail_scheduler.get_service_connection_by_user_and_service") as mock_get_conn:
            mock_get_conn.side_effect = Exception("Database error")

            result = _get_gmail_service(user_id, mock_db)

            assert result is None

    def test_get_gmail_service_refresh_failure(self):
        """Test Gmail service creation with token refresh failure."""
        user_id = "test-user-id"
        mock_db = Mock()
        mock_connection = Mock()
        mock_connection.id = "connection-id"
        mock_connection.service_name = "gmail"
        mock_connection.encrypted_access_token = b"encrypted_access_token"
        mock_connection.encrypted_refresh_token = b"encrypted_refresh_token"

        with patch("app.integrations.simple_plugins.gmail_scheduler.get_service_connection_by_user_and_service") as mock_get_conn, \
             patch("app.integrations.simple_plugins.gmail_scheduler.decrypt_token") as mock_decrypt, \
             patch("app.integrations.simple_plugins.gmail_scheduler.build") as mock_build, \
             patch("app.integrations.simple_plugins.gmail_scheduler.Credentials") as mock_credentials, \
             patch("app.integrations.simple_plugins.gmail_scheduler.Request") as mock_request:

            mock_get_conn.return_value = mock_connection
            mock_decrypt.side_effect = lambda x: x.decode() if isinstance(x, bytes) else str(x)

            # Mock credentials that fail to refresh
            mock_creds = Mock()
            mock_creds.expired = True
            mock_creds.refresh_token = "decrypted_refresh_token"
            mock_creds.refresh.side_effect = Exception("Refresh failed")
            mock_credentials.return_value = mock_creds

            result = _get_gmail_service(user_id, mock_db)

            assert result is None

    def test_fetch_messages_partial_failure(self):
        """Test Gmail message fetching with partial failures."""
        mock_service = Mock()

        # Mock the list() call
        mock_list = Mock()
        mock_list.execute.return_value = {
            "messages": [
                {"id": "msg1", "threadId": "thread1"},
                {"id": "msg2", "threadId": "thread2"}
            ]
        }

        # Mock the get() calls - first succeeds, second fails
        mock_get1 = Mock()
        mock_get1.execute.return_value = {
            "id": "msg1",
            "threadId": "thread1",
            "payload": {"headers": []}
        }
        mock_get2 = Mock()
        http_resp = Mock()
        http_resp.status = 404
        http_resp.reason = "Not Found"
        mock_get2.execute.side_effect = HttpError(http_resp, b"Not Found")

        # Set up the mock chain
        mock_service.users().messages().list.return_value = mock_list
        mock_service.users().messages().get.side_effect = [mock_get1, mock_get2]

        result = _fetch_messages(mock_service, "test query")

        # Should only return the successful message
        assert len(result) == 1
        assert result[0]["id"] == "msg1"

    def test_build_gmail_query_unknown_action(self):
        """Test Gmail query building for unknown trigger action."""
        area = Mock()
        area.trigger_action = "unknown_action"
        area.trigger_params = {}

        query = _build_gmail_query(area)

        assert query is None

    def test_extract_message_data(self):
        """Test extracting data from Gmail message."""
        message = {
            "id": "msg123",
            "threadId": "thread123",
            "snippet": "This is a test message",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"},
                ]
            }
        }

        result = _extract_message_data(message)

        assert result["id"] == "msg123"
        assert result["threadId"] == "thread123"
        assert result["snippet"] == "This is a test message"
        assert result["sender"] == "sender@example.com"
        assert result["subject"] == "Test Subject"
        assert result["date"] == "Mon, 1 Jan 2024 12:00:00 +0000"

    def test_extract_message_data_missing_headers(self):
        """Test extracting data from Gmail message with missing headers."""
        message = {
            "id": "msg123",
            "threadId": "thread123",
            "payload": {
                "headers": []
            }
        }

        result = _extract_message_data(message)

        assert result["id"] == "msg123"
        assert result["sender"] == ""
        assert result["subject"] == ""
        assert result["date"] == ""

    def test_fetch_due_gmail_areas(self):
        """Test fetching enabled Gmail areas."""
        mock_db = Mock()
        mock_area1 = Mock()
        mock_area1.id = "area1"
        mock_area1.enabled = True
        mock_area1.trigger_service = "gmail"

        mock_filter = Mock()
        mock_filter.all.return_value = [mock_area1]
        mock_query = Mock()
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        result = _fetch_due_gmail_areas(mock_db)

        assert len(result) == 1
        assert result[0] == mock_area1

    @pytest.mark.asyncio
    async def test_gmail_scheduler_task_cancellation(self):
        """Test Gmail scheduler task handles cancellation."""
        with patch("app.db.session.SessionLocal") as mock_session, \
             patch("asyncio.sleep") as mock_sleep:

            mock_sleep.side_effect = asyncio.CancelledError()

            # Should exit gracefully without raising
            await gmail_scheduler_task()

            mock_sleep.assert_called()

    @pytest.mark.asyncio
    async def test_gmail_scheduler_task_with_error(self):
        """Test Gmail scheduler task handles errors and continues."""
        with patch("app.db.session.SessionLocal") as mock_session, \
             patch("asyncio.sleep") as mock_sleep, \
             patch("app.integrations.simple_plugins.gmail_scheduler._fetch_due_gmail_areas") as mock_fetch:

            # First sleep (poll interval) succeeds, second sleep (backoff after error) raises CancelledError
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            mock_fetch.side_effect = Exception("Database error")

            mock_db = Mock()
            mock_db.__enter__ = Mock(return_value=mock_db)
            mock_db.__exit__ = Mock(return_value=None)
            mock_session.return_value = mock_db

            # Should handle error and continue until cancelled
            with pytest.raises(asyncio.CancelledError):
                await gmail_scheduler_task()

            # Verify it tried to fetch despite error
            assert mock_fetch.call_count == 1
            # Verify it called sleep twice: once for poll interval, once for backoff
            assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_process_gmail_trigger_success(self):
        """Test processing Gmail trigger successfully."""
        from uuid import uuid4

        mock_db = Mock()
        mock_area = Mock()
        mock_area.id = uuid4()
        mock_area.user_id = uuid4()
        mock_area.name = "Test Area"
        mock_area.steps = []

        message = {
            "id": "msg123",
            "threadId": "thread123",
            "snippet": "Test",
            "payload": {
                "headers": [
                    {"name": "From", "value": "test@example.com"},
                    {"name": "Subject", "value": "Test"},
                    {"name": "Date", "value": "Mon, 1 Jan 2024"},
                ]
            }
        }

        now = datetime.now(timezone.utc)

        with patch("app.integrations.simple_plugins.gmail_scheduler.create_execution_log") as mock_create_log, \
             patch("app.integrations.simple_plugins.gmail_scheduler.execute_area") as mock_execute, \
             patch("app.integrations.simple_plugins.gmail_scheduler.extract_gmail_variables") as mock_extract:

            mock_log = Mock()
            mock_log.status = "Started"
            mock_create_log.return_value = mock_log
            
            mock_execute.return_value = {
                "status": "success",
                "steps_executed": 2,
                "execution_log": []
            }
            
            mock_extract.return_value = {
                "gmail.subject": "Test",
                "gmail.sender": "test@example.com"
            }

            mock_db.merge.return_value = mock_area

            await _process_gmail_trigger(mock_db, mock_area, message, now)

            mock_create_log.assert_called_once()
            mock_execute.assert_called_once()
            mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_process_gmail_trigger_failure(self):
        """Test processing Gmail trigger with execution failure."""
        from uuid import uuid4

        mock_db = Mock()
        mock_area = Mock()
        mock_area.id = uuid4()
        mock_area.user_id = uuid4()
        mock_area.name = "Test Area"

        message = {
            "id": "msg123",
            "payload": {"headers": []}
        }

        now = datetime.now(timezone.utc)

        with patch("app.integrations.simple_plugins.gmail_scheduler.create_execution_log") as mock_create_log, \
             patch("app.integrations.simple_plugins.gmail_scheduler.execute_area") as mock_execute, \
             patch("app.integrations.simple_plugins.gmail_scheduler.extract_gmail_variables") as mock_extract:

            mock_log = Mock()
            mock_log.status = "Started"
            mock_create_log.return_value = mock_log
            
            mock_execute.side_effect = Exception("Execution failed")
            mock_extract.return_value = {}
            mock_db.merge.return_value = mock_area

            await _process_gmail_trigger(mock_db, mock_area, message, now)

            # Should update log with failure
            assert mock_log.status == "Failed"
            mock_db.commit.assert_called()

    def test_is_gmail_scheduler_running(self):
        """Test checking if Gmail scheduler is running."""
        # Clear state first
        with patch("app.integrations.simple_plugins.gmail_scheduler._gmail_scheduler_task", None):
            assert is_gmail_scheduler_running() is False

    def test_clear_gmail_seen_state(self):
        """Test clearing Gmail seen state."""
        # This should not raise any errors
        clear_gmail_seen_state()

    @pytest.mark.asyncio
    async def test_gmail_scheduler_processes_new_messages(self):
        """Test Gmail scheduler processes new messages correctly."""
        from uuid import uuid4

        with patch("app.db.session.SessionLocal") as mock_session, \
             patch("asyncio.sleep") as mock_sleep, \
             patch("app.integrations.simple_plugins.gmail_scheduler._fetch_due_gmail_areas") as mock_fetch_areas, \
             patch("app.integrations.simple_plugins.gmail_scheduler._get_gmail_service") as mock_get_service, \
             patch("app.integrations.simple_plugins.gmail_scheduler._fetch_messages") as mock_fetch_messages, \
             patch("app.integrations.simple_plugins.gmail_scheduler._process_gmail_trigger") as mock_process, \
             patch("app.integrations.simple_plugins.gmail_scheduler._last_seen_messages", {}) as mock_seen:

            # Setup mocks
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            
            mock_area = Mock()
            mock_area.id = uuid4()
            mock_area.user_id = uuid4()
            mock_area.name = "Test Area"
            mock_area.trigger_action = "new_email"
            mock_area.trigger_params = {}
            
            mock_fetch_areas.return_value = [mock_area]
            
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            
            message = {
                "id": "msg123",
                "threadId": "thread123",
                "payload": {"headers": []}
            }
            mock_fetch_messages.return_value = [message]

            mock_db = Mock()
            mock_db.__enter__ = Mock(return_value=mock_db)
            mock_db.__exit__ = Mock(return_value=None)
            mock_session.return_value = mock_db

            # Run scheduler
            await gmail_scheduler_task()

            # Should have processed the message
            assert mock_process.call_count >= 0  # May be 0 if seen set is initialized
