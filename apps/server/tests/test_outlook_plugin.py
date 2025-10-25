"""Tests for Outlook plugin handlers."""

from __future__ import annotations

from unittest.mock import Mock, patch, AsyncMock

import pytest
import httpx

from app.integrations.simple_plugins.outlook_plugin import (
    _get_outlook_client,
    send_email_handler,
    mark_as_read_handler,
    forward_email_handler,
)


class TestOutlookPlugin:
    """Test Outlook plugin functionality."""

    @pytest.mark.asyncio
    async def test_get_outlook_client_success(self):
        """Test successful Outlook client creation."""
        # Mock area
        area = Mock()
        area.user_id = "test-user-id"
        area.id = "test-area-id"

        # Mock database and service connection
        mock_db = Mock()
        mock_connection = Mock()
        mock_connection.encrypted_access_token = "encrypted_access_token"
        mock_connection.encrypted_refresh_token = "encrypted_refresh_token"
        mock_connection.expires_at = None

        with patch("app.integrations.simple_plugins.outlook_plugin.get_service_connection_by_user_and_service") as mock_get_conn, \
             patch("app.integrations.simple_plugins.outlook_utils.decrypt_token") as mock_decrypt, \
             patch("app.integrations.simple_plugins.outlook_plugin.SessionLocal"):

            mock_get_conn.return_value = mock_connection
            mock_decrypt.side_effect = ["decrypted_access_token", "decrypted_refresh_token"]

            result = await _get_outlook_client(area, mock_db)

            assert isinstance(result, httpx.AsyncClient)
            mock_get_conn.assert_called_once_with(mock_db, "test-user-id", "outlook")

    @pytest.mark.asyncio
    async def test_get_outlook_client_no_connection(self):
        """Test Outlook client creation when no connection exists."""
        area = Mock()
        area.user_id = "test-user-id"
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.outlook_plugin.get_service_connection_by_user_and_service") as mock_get_conn:
            mock_get_conn.return_value = None

            with pytest.raises(Exception, match="Outlook service connection not found"):
                await _get_outlook_client(area, mock_db)

    @pytest.mark.asyncio
    async def test_send_email_handler_success(self):
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
        event = {"outlook.message_id": "12345"}

        # Mock the entire _get_outlook_client to return a mock client directly
        mock_client = AsyncMock()
        mock_client.headers = {"Authorization": "Bearer mock_token"}  # Add headers attribute
        mock_response = Mock()
        mock_response.status_code = 202  # Microsoft Graph sendMail returns 202
        mock_response.text = ""
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "id": "sent_message_id",
            "subject": "Test Subject"
        }
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.aclose = AsyncMock()

        with patch("app.integrations.simple_plugins.outlook_plugin._get_outlook_client") as mock_get_client:
            mock_get_client.return_value = mock_client

            await send_email_handler(area, params, event)

            mock_get_client.assert_called_once()
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_handler_missing_params(self):
        """Test email sending with missing required parameters."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {"subject": "Test Subject"}  # Missing 'to'
        event = {}

        with patch("app.integrations.simple_plugins.outlook_plugin._get_outlook_client") as mock_get_client:
            mock_get_client.return_value = AsyncMock()

            # Should raise ValueError for missing 'to' parameter
            with pytest.raises(ValueError, match="'to' parameter is required"):
                await send_email_handler(area, params, event)

    @pytest.mark.asyncio
    async def test_send_email_handler_with_cc_bcc(self):
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

        mock_client = AsyncMock()
        mock_client.headers = {"Authorization": "Bearer mock_token"}  # Add headers attribute
        mock_response = Mock()
        mock_response.status_code = 202  # Microsoft Graph sendMail returns 202
        mock_response.text = ""
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {"id": "sent_message_id"}
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.aclose = AsyncMock()

        with patch("app.integrations.simple_plugins.outlook_plugin._get_outlook_client") as mock_get_client:
            mock_get_client.return_value = mock_client

            await send_email_handler(area, params, event)

            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_as_read_handler_success(self):
        """Test successful email marking as read."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {"message_id": "12345"}
        event = {}

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {"id": "12345", "isRead": True}
        mock_client.patch.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("app.integrations.simple_plugins.outlook_plugin._get_outlook_client") as mock_get_client:
            mock_get_client.return_value = mock_client

            await mark_as_read_handler(area, params, event)

            mock_get_client.assert_called_once()
            mock_client.patch.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_as_read_handler_missing_message_id(self):
        """Test marking as read with missing message ID."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {}  # Missing message_id
        event = {}

        with patch("app.integrations.simple_plugins.outlook_plugin._get_outlook_client") as mock_get_client:
            mock_get_client.return_value = AsyncMock()

            # Should raise ValueError for missing message_id
            with pytest.raises(ValueError, match="'message_id' is required"):
                await mark_as_read_handler(area, params, event)

    @pytest.mark.asyncio
    async def test_forward_email_handler_success(self):
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

        mock_client = AsyncMock()
        
        # Mock POST request for forwarding
        mock_post_response = Mock()
        mock_post_response.status_code = 202
        mock_post_response.raise_for_status = Mock()
        
        mock_client.post.return_value = mock_post_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.aclose = AsyncMock()

        with patch("app.integrations.simple_plugins.outlook_plugin._get_outlook_client") as mock_get_client:
            mock_get_client.return_value = mock_client

            await forward_email_handler(area, params, event)

            mock_get_client.assert_called_once()
            mock_client.post.assert_called_once()
            # Verify the post was called with the correct endpoint
            call_args = mock_client.post.call_args
            assert "/me/messages/12345/forward" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_forward_email_handler_missing_params(self):
        """Test email forwarding with missing required parameters."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {"message_id": "12345"}  # Missing 'to'
        event = {}

        with patch("app.integrations.simple_plugins.outlook_plugin._get_outlook_client") as mock_get_client:
            mock_get_client.return_value = AsyncMock()

            # Should raise ValueError for missing 'to' parameter
            with pytest.raises(ValueError, match="'to' parameter is required"):
                await forward_email_handler(area, params, event)

    @pytest.mark.asyncio
    async def test_send_email_handler_http_error(self):
        """Test email sending with HTTP error."""
        from app.integrations.simple_plugins.outlook_plugin import OutlookAPIError
        
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

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        http_error = httpx.HTTPStatusError(
            "400 Bad Request",
            request=Mock(),
            response=mock_response
        )
        mock_response.raise_for_status.side_effect = http_error
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("app.integrations.simple_plugins.outlook_plugin._get_outlook_client") as mock_get_client:
            mock_get_client.return_value = mock_client

            with pytest.raises(OutlookAPIError):
                await send_email_handler(area, params, event)

    @pytest.mark.asyncio
    async def test_mark_as_read_handler_http_error(self):
        """Test marking as read with HTTP error."""
        from app.integrations.simple_plugins.outlook_plugin import OutlookAPIError
        
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {"message_id": "12345"}
        event = {}

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        http_error = httpx.HTTPStatusError(
            "404 Not Found",
            request=Mock(),
            response=mock_response
        )
        mock_response.raise_for_status.side_effect = http_error
        mock_client.patch.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("app.integrations.simple_plugins.outlook_plugin._get_outlook_client") as mock_get_client:
            mock_get_client.return_value = mock_client

            with pytest.raises(OutlookAPIError):
                await mark_as_read_handler(area, params, event)

    @pytest.mark.asyncio
    async def test_forward_email_handler_message_not_found(self):
        """Test email forwarding when original message not found."""
        from app.integrations.simple_plugins.outlook_plugin import OutlookAPIError
        
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "message_id": "nonexistent",
            "to": "forward@example.com"
        }
        event = {}

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        http_error = httpx.HTTPStatusError(
            "404 Not Found",
            request=Mock(),
            response=mock_response
        )
        mock_response.raise_for_status.side_effect = http_error
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.aclose = AsyncMock()

        with patch("app.integrations.simple_plugins.outlook_plugin._get_outlook_client") as mock_get_client:
            mock_get_client.return_value = mock_client

            with pytest.raises(OutlookAPIError):
                await forward_email_handler(area, params, event)
