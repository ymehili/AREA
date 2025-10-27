"""Tests for Outlook scheduler functionality."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock

import pytest
import httpx

from app.integrations.simple_plugins.outlook_scheduler import (
    _get_outlook_client,
    _fetch_messages,
    _build_outlook_filter,
    start_outlook_scheduler,
    stop_outlook_scheduler,
)


class TestOutlookScheduler:
    """Test Outlook scheduler functionality."""

    @pytest.mark.asyncio
    async def test_get_outlook_client_success(self):
        """Test successful Outlook client creation."""
        user_id = "test-user-id"
        mock_db = Mock()
        mock_connection = Mock()
        mock_connection.encrypted_access_token = "encrypted_access_token"
        mock_connection.encrypted_refresh_token = "encrypted_refresh_token"
        mock_connection.expires_at = None

        with patch("app.integrations.simple_plugins.outlook_scheduler.get_service_connection_by_user_and_service") as mock_get_conn, \
             patch("app.integrations.simple_plugins.outlook_utils.decrypt_token") as mock_decrypt:

            mock_get_conn.return_value = mock_connection
            mock_decrypt.side_effect = ["decrypted_access_token", "decrypted_refresh_token"]

            result = await _get_outlook_client(user_id, mock_db)

            assert result is not None
            assert isinstance(result, httpx.AsyncClient)
            mock_get_conn.assert_called_once_with(mock_db, user_id, "outlook")

    @pytest.mark.asyncio
    async def test_get_outlook_client_no_connection(self):
        """Test Outlook client creation when no connection exists."""
        user_id = "test-user-id"
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.outlook_scheduler.get_service_connection_by_user_and_service") as mock_get_conn:
            mock_get_conn.return_value = None

            result = await _get_outlook_client(user_id, mock_db)

            assert result is None

    def test_build_outlook_filter_new_email(self):
        """Test Outlook filter building for new email trigger."""
        area = Mock()
        area.trigger_action = "new_email"
        area.trigger_params = {}

        filter_str = _build_outlook_filter(area)

        assert "receivedDateTime ge" in filter_str

    def test_build_outlook_filter_new_email_from_sender(self):
        """Test Outlook filter building for new email from sender trigger."""
        area = Mock()
        area.trigger_action = "new_email_from_sender"
        area.trigger_params = {"sender_email": "test@example.com"}

        filter_str = _build_outlook_filter(area)

        assert "from/emailAddress/address eq 'test@example.com'" in filter_str

    def test_build_outlook_filter_new_email_from_sender_no_email(self):
        """Test Outlook filter building for new email from sender without email."""
        area = Mock()
        area.trigger_action = "new_email_from_sender"
        area.trigger_params = {}

        filter_str = _build_outlook_filter(area)

        # Should fall back to default filter
        assert "receivedDateTime ge" in filter_str

    def test_build_outlook_filter_new_unread_email(self):
        """Test Outlook filter building for new unread email trigger."""
        area = Mock()
        area.trigger_action = "new_unread_email"
        area.trigger_params = {}

        filter_str = _build_outlook_filter(area)

        assert "isRead eq false" in filter_str

    def test_build_outlook_filter_email_flagged(self):
        """Test Outlook filter building for flagged email trigger."""
        area = Mock()
        area.trigger_action = "email_flagged"
        area.trigger_params = {}

        filter_str = _build_outlook_filter(area)

        assert "flag/flagStatus eq 'flagged'" in filter_str

    @pytest.mark.asyncio
    async def test_fetch_messages_success(self):
        """Test successful Outlook message fetching."""
        mock_client = AsyncMock()

        # Mock the API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "msg1",
                    "subject": "Test 1",
                    "receivedDateTime": "2025-10-14T12:00:00Z"
                },
                {
                    "id": "msg2",
                    "subject": "Test 2",
                    "receivedDateTime": "2025-10-14T13:00:00Z"
                }
            ]
        }
        mock_client.get.return_value = mock_response

        result = await _fetch_messages(mock_client, "isRead eq false")

        assert len(result) == 2
        assert result[0]["id"] == "msg1"
        assert result[1]["id"] == "msg2"

    @pytest.mark.asyncio
    async def test_fetch_messages_no_messages(self):
        """Test Outlook message fetching when no messages found."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": []}
        mock_client.get.return_value = mock_response

        result = await _fetch_messages(mock_client, "isRead eq false")

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_messages_http_error(self):
        """Test Outlook message fetching with HTTP error."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request",
            request=Mock(),
            response=mock_response
        )
        mock_client.get.return_value = mock_response

        result = await _fetch_messages(mock_client, "invalid filter")

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_messages_pagination(self):
        """Test Outlook message fetching with pagination."""
        mock_client = AsyncMock()

        # Mock first page response
        mock_response_1 = Mock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = {
            "value": [
                {"id": "msg1", "subject": "Test 1"}
            ],
            "@odata.nextLink": "https://graph.microsoft.com/v1.0/me/messages?$skip=10"
        }

        # Mock second page response
        mock_response_2 = Mock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = {
            "value": [
                {"id": "msg2", "subject": "Test 2"}
            ]
        }

        mock_client.get.side_effect = [mock_response_1, mock_response_2]

        result = await _fetch_messages(mock_client, "isRead eq false")

        # Should only return first page (based on actual implementation)
        assert len(result) == 1
        assert result[0]["id"] == "msg1"

    @pytest.mark.asyncio
    async def test_fetch_messages_with_top_param(self):
        """Test Outlook message fetching with $top parameter."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": f"msg{i}", "subject": f"Test {i}"} 
                for i in range(50)
            ]
        }
        mock_client.get.return_value = mock_response

        result = await _fetch_messages(mock_client, "isRead eq false")

        # Should respect the $top=50 limit
        assert len(result) <= 50

    @pytest.mark.asyncio
    async def test_fetch_messages_unauthorized(self):
        """Test Outlook message fetching with unauthorized error."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=Mock(),
            response=mock_response
        )
        mock_client.get.return_value = mock_response

        result = await _fetch_messages(mock_client, "isRead eq false")

        assert result == []

    def test_build_outlook_filter_unknown_trigger(self):
        """Test Outlook filter building for unknown trigger type."""
        area = Mock()
        area.trigger_action = "unknown_trigger"
        area.trigger_params = {}

        filter_str = _build_outlook_filter(area)

        # Should return default filter
        assert "receivedDateTime ge" in filter_str

    @pytest.mark.asyncio
    async def test_fetch_messages_empty_value(self):
        """Test Outlook message fetching with missing 'value' key."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # No 'value' key
        mock_client.get.return_value = mock_response

        result = await _fetch_messages(mock_client, "isRead eq false")

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_messages_with_select_param(self):
        """Test that fetch_messages includes proper OData parameters."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "msg1",
                    "subject": "Test",
                    "from": {"emailAddress": {"address": "test@example.com"}},
                    "receivedDateTime": "2025-10-14T12:00:00Z",
                    "isRead": False,
                    "importance": "normal",
                    "hasAttachments": False,
                    "bodyPreview": "Test preview"
                }
            ]
        }
        mock_client.get.return_value = mock_response

        result = await _fetch_messages(mock_client, "isRead eq false")

        # Verify the API was called
        assert len(result) == 1
        mock_client.get.assert_called_once()
        # Check that the call was made with proper parameters
        call_args = mock_client.get.call_args
        assert call_args[0][0] == "/me/messages"
        # Verify params were passed
        assert "params" in call_args[1]
        params = call_args[1]["params"]
        assert "$filter" in params
        assert params["$filter"] == "isRead eq false"
        assert "$top" in params
        assert "$orderby" in params
