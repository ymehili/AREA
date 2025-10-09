"""Tests for Gmail plugin handlers."""

from __future__ import annotations

import base64
from unittest.mock import Mock, patch, MagicMock

import pytest
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

from app.integrations.simple_plugins.gmail_plugin import (
    _get_gmail_service,
    send_email_handler,
    mark_as_read_handler,
    forward_email_handler,
)


class TestGmailPlugin:
    """Test Gmail plugin functionality."""

    def test_get_gmail_service_success(self):
        """Test successful Gmail service creation."""
        # Mock area
        area = Mock()
        area.user_id = "test-user-id"

        # Mock database and service connection
        mock_db = Mock()
        mock_connection = Mock()
        mock_connection.encrypted_access_token = b"encrypted_access_token"
        mock_connection.encrypted_refresh_token = b"encrypted_refresh_token"

        with patch("app.integrations.simple_plugins.gmail_plugin.get_service_connection_by_user_and_service") as mock_get_conn, \
             patch("app.core.encryption.decrypt_token") as mock_decrypt, \
             patch("app.integrations.simple_plugins.gmail_plugin.build") as mock_build, \
             patch("app.integrations.simple_plugins.gmail_plugin.Credentials") as mock_credentials:

            mock_get_conn.return_value = mock_connection
            mock_decrypt.side_effect = ["decrypted_access_token", "decrypted_refresh_token"]

            mock_creds = Mock()
            mock_creds.expired = False
            mock_creds.refresh_token = "decrypted_refresh_token"
            mock_credentials.return_value = mock_creds

            mock_service = Mock()
            mock_build.return_value = mock_service

            result = _get_gmail_service(area, mock_db)

            assert result == mock_service
            mock_get_conn.assert_called_once_with(mock_db, "test-user-id", "gmail")

    def test_get_gmail_service_no_connection(self):
        """Test Gmail service creation when no connection exists."""
        area = Mock()
        area.user_id = "test-user-id"
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.gmail_plugin.get_service_connection_by_user_and_service") as mock_get_conn:
            mock_get_conn.return_value = None

            with pytest.raises(Exception, match="Gmail service connection not found"):
                _get_gmail_service(area, mock_db)

    def test_get_gmail_service_token_refresh(self):
        """Test Gmail service creation with token refresh."""
        area = Mock()
        area.user_id = "test-user-id"
        mock_db = Mock()
        mock_connection = Mock()
        mock_connection.id = "connection-id"
        mock_connection.service_name = "gmail"
        mock_connection.encrypted_access_token = b"encrypted_access_token"
        mock_connection.encrypted_refresh_token = b"encrypted_refresh_token"

        with patch("app.integrations.simple_plugins.gmail_plugin.get_service_connection_by_user_and_service") as mock_get_conn, \
             patch("app.core.encryption.decrypt_token") as mock_decrypt, \
             patch("app.integrations.simple_plugins.gmail_plugin.build") as mock_build, \
             patch("app.integrations.simple_plugins.gmail_plugin.Credentials") as mock_credentials, \
             patch("app.integrations.simple_plugins.gmail_plugin.update_service_connection") as mock_update, \
             patch("app.integrations.simple_plugins.gmail_plugin.Request") as mock_request:

            mock_get_conn.return_value = mock_connection
            mock_decrypt.side_effect = ["decrypted_access_token", "decrypted_refresh_token"]

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

            result = _get_gmail_service(area, mock_db)

            assert result == mock_service
            mock_creds.refresh.assert_called_once()
            mock_update.assert_called_once()

    def test_send_email_handler_success(self):
        """Test successful email sending."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "to": "recipient@example.com",
            "subject": "Test Subject",
            "body": "Test body content"
        }
        event = {"gmail.message_id": "12345"}

        mock_service = Mock()
        mock_send = Mock()
        mock_send.execute.return_value = {"id": "sent_message_id", "threadId": "thread_id"}
        mock_service.users().messages().send.return_value = mock_send

        with patch("app.integrations.simple_plugins.gmail_plugin._get_gmail_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            send_email_handler(area, params, event)

            mock_get_service.assert_called_once_with(area)
            mock_send.execute.assert_called_once()

    def test_send_email_handler_missing_params(self):
        """Test email sending with missing required parameters."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {"subject": "Test Subject"}  # Missing 'to'
        event = {}

        with patch("app.integrations.simple_plugins.gmail_plugin._get_gmail_service") as mock_get_service:
            mock_get_service.return_value = Mock()

            # Should raise ValueError for missing 'to' parameter
            with pytest.raises(ValueError, match="'to' parameter is required"):
                send_email_handler(area, params, event)

    def test_send_email_handler_with_cc_bcc(self):
        """Test email sending with CC and BCC."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "to": "recipient@example.com",
            "subject": "Test Subject",
            "body": "Test body content",
            "cc": "cc@example.com",
            "bcc": "bcc@example.com"
        }
        event = {}

        mock_service = Mock()
        mock_send = Mock()
        mock_send.execute.return_value = {"id": "sent_message_id"}
        mock_service.users().messages().send.return_value = mock_send

        with patch("app.integrations.simple_plugins.gmail_plugin._get_gmail_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            send_email_handler(area, params, event)

            mock_send.execute.assert_called_once()

    def test_mark_as_read_handler_success(self):
        """Test successful email marking as read."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {"message_id": "12345"}
        event = {}

        mock_service = Mock()
        mock_modify = Mock()
        mock_modify.execute.return_value = {"id": "12345"}
        mock_service.users().messages().modify.return_value = mock_modify

        with patch("app.integrations.simple_plugins.gmail_plugin._get_gmail_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            mark_as_read_handler(area, params, event)

            mock_get_service.assert_called_once_with(area)
            mock_modify.execute.assert_called_once()

    def test_mark_as_read_handler_missing_message_id(self):
        """Test marking as read with missing message ID."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {}  # Missing message_id
        event = {}

        with patch("app.integrations.simple_plugins.gmail_plugin._get_gmail_service") as mock_get_service:
            mock_get_service.return_value = Mock()

            # Should raise ValueError for missing message_id
            with pytest.raises(ValueError, match="'message_id' is required"):
                mark_as_read_handler(area, params, event)

    def test_forward_email_handler_success(self):
        """Test successful email forwarding."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "message_id": "12345",
            "to": "forward@example.com",
            "comment": "Forwarding this email"
        }
        event = {}

        mock_service = Mock()
        mock_get = Mock()
        mock_get.execute.return_value = {
            "id": "12345",
            "threadId": "thread_id",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Original Subject"},
                    {"name": "From", "value": "original@example.com"}
                ],
                "body": {"data": base64.urlsafe_b64encode(b"Original body").decode()}
            }
        }
        mock_send = Mock()
        mock_send.execute.return_value = {"id": "forwarded_id"}
        mock_service.users().messages().get.return_value = mock_get
        mock_service.users().messages().send.return_value = mock_send

        with patch("app.integrations.simple_plugins.gmail_plugin._get_gmail_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            forward_email_handler(area, params, event)

            mock_get_service.assert_called_once_with(area)
            mock_get.execute.assert_called_once()
            mock_send.execute.assert_called_once()

    def test_forward_email_handler_missing_params(self):
        """Test email forwarding with missing required parameters."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {"message_id": "12345"}  # Missing 'to'
        event = {}

        with patch("app.integrations.simple_plugins.gmail_plugin._get_gmail_service") as mock_get_service:
            mock_get_service.return_value = Mock()

            # Should raise ValueError for missing 'to' parameter
            with pytest.raises(ValueError, match="'to' parameter is required"):
                forward_email_handler(area, params, event)

    def test_send_email_handler_http_error(self):
        """Test email sending with HTTP error."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "to": "recipient@example.com",
            "subject": "Test Subject",
            "body": "Test body content"
        }
        event = {}

        mock_service = Mock()
        mock_send = Mock()
        http_resp = Mock()
        http_resp.status = 400
        http_resp.reason = "Bad Request"
        mock_send.execute.side_effect = HttpError(http_resp, b"Bad Request")
        mock_service.users().messages().send.return_value = mock_send

        with patch("app.integrations.simple_plugins.gmail_plugin._get_gmail_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            # Should raise Exception wrapping HttpError
            with pytest.raises(Exception, match="Failed to send email"):
                send_email_handler(area, params, event)

    def test_mark_as_read_handler_http_error(self):
        """Test marking as read with HTTP error."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {"message_id": "12345"}
        event = {}

        mock_service = Mock()
        mock_modify = Mock()
        http_resp = Mock()
        http_resp.status = 404
        http_resp.reason = "Not Found"
        mock_modify.execute.side_effect = HttpError(http_resp, b"Not Found")
        mock_service.users().messages().modify.return_value = mock_modify

        with patch("app.integrations.simple_plugins.gmail_plugin._get_gmail_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            # Should raise Exception wrapping HttpError
            with pytest.raises(Exception, match="Failed to mark email as read"):
                mark_as_read_handler(area, params, event)

    def test_forward_email_handler_http_error(self):
        """Test email forwarding with HTTP error."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "message_id": "12345",
            "to": "forward@example.com",
            "comment": "Forwarding this email"
        }
        event = {}

        mock_service = Mock()
        mock_get = Mock()
        http_resp = Mock()
        http_resp.status = 404
        http_resp.reason = "Not Found"
        mock_get.execute.side_effect = HttpError(http_resp, b"Not Found")
        mock_service.users().messages().get.return_value = mock_get

        with patch("app.integrations.simple_plugins.gmail_plugin._get_gmail_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            # Should raise Exception wrapping HttpError
            with pytest.raises(Exception, match="Failed to forward email"):
                forward_email_handler(area, params, event)

    def test_get_gmail_service_http_error(self):
        """Test Gmail service creation with HTTP error during token refresh."""
        area = Mock()
        area.user_id = "test-user-id"
        mock_db = Mock()
        mock_connection = Mock()
        mock_connection.id = "connection-id"
        mock_connection.service_name = "gmail"
        mock_connection.encrypted_access_token = b"encrypted_access_token"
        mock_connection.encrypted_refresh_token = b"encrypted_refresh_token"

        with patch("app.integrations.simple_plugins.gmail_plugin.get_service_connection_by_user_and_service") as mock_get_conn, \
             patch("app.core.encryption.decrypt_token") as mock_decrypt, \
             patch("app.integrations.simple_plugins.gmail_plugin.Credentials") as mock_credentials, \
             patch("app.integrations.simple_plugins.gmail_plugin.Request") as mock_request:

            mock_get_conn.return_value = mock_connection
            mock_decrypt.side_effect = ["decrypted_access_token", "decrypted_refresh_token"]

            # Mock credentials that need refresh but fail
            mock_creds = Mock()
            mock_creds.expired = True
            mock_creds.refresh_token = "decrypted_refresh_token"
            http_resp = Mock()
            http_resp.status = 400
            http_resp.reason = "Invalid refresh token"
            mock_creds.refresh.side_effect = Exception("Failed to refresh Gmail token")
            mock_credentials.return_value = mock_creds

            with pytest.raises(Exception, match="Failed to refresh Gmail token"):
                _get_gmail_service(area, mock_db)
