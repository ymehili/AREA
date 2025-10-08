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
    start_gmail_scheduler,
    stop_gmail_scheduler,
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
