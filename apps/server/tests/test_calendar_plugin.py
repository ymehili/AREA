"""Tests for Google Calendar plugin handlers."""

from __future__ import annotations

from unittest.mock import Mock, patch
from datetime import datetime

import pytest
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

from app.integrations.simple_plugins.calendar_plugin import (
    _get_calendar_service,
    create_event_handler,
    update_event_handler,
    delete_event_handler,
    create_all_day_event_handler,
    quick_add_event_handler,
)
from app.integrations.simple_plugins.exceptions import (
    CalendarAuthError,
    CalendarAPIError,
    CalendarConnectionError,
)


class TestCalendarPlugin:
    """Test Google Calendar plugin functionality."""

    def test_get_calendar_service_success(self):
        """Test successful Calendar service creation."""
        # Mock area
        area = Mock()
        area.user_id = "test-user-id"

        # Mock database and service connection
        mock_db = Mock()
        mock_connection = Mock()
        mock_connection.encrypted_access_token = b"encrypted_access_token"
        mock_connection.encrypted_refresh_token = b"encrypted_refresh_token"

        with patch("app.integrations.simple_plugins.calendar_plugin.get_service_connection_by_user_and_service") as mock_get_conn, \
             patch("app.core.encryption.decrypt_token") as mock_decrypt, \
             patch("app.integrations.simple_plugins.calendar_plugin.build") as mock_build, \
             patch("app.integrations.simple_plugins.calendar_plugin.Credentials") as mock_credentials:

            mock_get_conn.return_value = mock_connection
            mock_decrypt.side_effect = ["decrypted_access_token", "decrypted_refresh_token"]

            mock_creds = Mock()
            mock_creds.expired = False
            mock_creds.refresh_token = "decrypted_refresh_token"
            mock_credentials.return_value = mock_creds

            mock_service = Mock()
            mock_build.return_value = mock_service

            result = _get_calendar_service(area, mock_db)

            assert result == mock_service
            mock_get_conn.assert_called_once_with(mock_db, "test-user-id", "google_calendar")

    def test_get_calendar_service_no_connection(self):
        """Test Calendar service creation when no connection exists."""
        area = Mock()
        area.user_id = "test-user-id"
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.calendar_plugin.get_service_connection_by_user_and_service") as mock_get_conn:
            mock_get_conn.return_value = None

            with pytest.raises(CalendarConnectionError, match="Google Calendar service connection not found"):
                _get_calendar_service(area, mock_db)

    def test_get_calendar_service_token_refresh(self):
        """Test Calendar service creation with token refresh."""
        area = Mock()
        area.user_id = "test-user-id"
        area.id = "test-area-id"
        mock_db = Mock()
        mock_connection = Mock()
        mock_connection.id = "connection-id"
        mock_connection.service_name = "google_calendar"
        mock_connection.encrypted_access_token = b"encrypted_access_token"
        mock_connection.encrypted_refresh_token = b"encrypted_refresh_token"

        with patch("app.integrations.simple_plugins.calendar_plugin.get_service_connection_by_user_and_service") as mock_get_conn, \
             patch("app.core.encryption.decrypt_token") as mock_decrypt, \
             patch("app.integrations.simple_plugins.calendar_plugin.build") as mock_build, \
             patch("app.integrations.simple_plugins.calendar_plugin.Credentials") as mock_credentials, \
             patch("app.integrations.simple_plugins.calendar_plugin.update_service_connection") as mock_update, \
             patch("app.integrations.simple_plugins.calendar_plugin.Request") as mock_request:

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

            result = _get_calendar_service(area, mock_db)

            assert result == mock_service
            mock_creds.refresh.assert_called_once()
            mock_update.assert_called_once()

    def test_get_calendar_service_refresh_failure(self):
        """Test Calendar service creation when token refresh fails."""
        area = Mock()
        area.user_id = "test-user-id"
        area.id = "test-area-id"
        mock_db = Mock()
        mock_connection = Mock()
        mock_connection.id = "connection-id"
        mock_connection.service_name = "google_calendar"
        mock_connection.encrypted_access_token = b"encrypted_access_token"
        mock_connection.encrypted_refresh_token = b"encrypted_refresh_token"

        with patch("app.integrations.simple_plugins.calendar_plugin.get_service_connection_by_user_and_service") as mock_get_conn, \
             patch("app.core.encryption.decrypt_token") as mock_decrypt, \
             patch("app.integrations.simple_plugins.calendar_plugin.Credentials") as mock_credentials:

            mock_get_conn.return_value = mock_connection
            mock_decrypt.side_effect = ["decrypted_access_token", "decrypted_refresh_token"]

            # Mock credentials that fail to refresh
            mock_creds = Mock()
            mock_creds.expired = True
            mock_creds.refresh_token = "decrypted_refresh_token"
            mock_creds.refresh.side_effect = Exception("Refresh failed")
            mock_credentials.return_value = mock_creds

            with pytest.raises(CalendarAuthError, match="Failed to refresh Google Calendar token"):
                _get_calendar_service(area, mock_db)

    def test_create_event_handler_success(self):
        """Test successful event creation."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "title": "Team Meeting",
            "start_time": "2025-10-21T10:00:00Z",
            "end_time": "2025-10-21T11:00:00Z",
            "description": "Discuss project updates",
            "location": "Conference Room A",
            "attendees": "alice@example.com,bob@example.com"
        }
        event = {}

        mock_service = Mock()
        mock_insert = Mock()
        mock_insert.execute.return_value = {
            "id": "event_id_123",
            "htmlLink": "https://calendar.google.com/event?eid=abc123"
        }
        mock_service.events().insert.return_value = mock_insert

        with patch("app.integrations.simple_plugins.calendar_plugin._get_calendar_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            create_event_handler(area, params, event)

            mock_get_service.assert_called_once_with(area)
            mock_insert.execute.assert_called_once()

    def test_create_event_handler_missing_title(self):
        """Test event creation with missing title."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "start_time": "2025-10-21T10:00:00Z",
            "end_time": "2025-10-21T11:00:00Z",
        }
        event = {}

        with patch("app.integrations.simple_plugins.calendar_plugin._get_calendar_service") as mock_get_service:
            mock_get_service.return_value = Mock()

            with pytest.raises(ValueError, match="'title' parameter is required"):
                create_event_handler(area, params, event)

    def test_create_event_handler_missing_times(self):
        """Test event creation with missing start/end times."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "title": "Team Meeting",
        }
        event = {}

        with patch("app.integrations.simple_plugins.calendar_plugin._get_calendar_service") as mock_get_service:
            mock_get_service.return_value = Mock()

            with pytest.raises(ValueError, match="'start_time' parameter is required"):
                create_event_handler(area, params, event)

    def test_create_event_handler_api_error(self):
        """Test event creation with API error."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "title": "Team Meeting",
            "start_time": "2025-10-21T10:00:00Z",
            "end_time": "2025-10-21T11:00:00Z",
        }
        event = {}

        mock_service = Mock()
        mock_insert = Mock()
        mock_response = Mock()
        mock_response.status = 403
        mock_insert.execute.side_effect = HttpError(resp=mock_response, content=b'Forbidden')
        mock_service.events().insert.return_value = mock_insert

        with patch("app.integrations.simple_plugins.calendar_plugin._get_calendar_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            with pytest.raises(CalendarAPIError, match="Failed to create calendar event"):
                create_event_handler(area, params, event)

    def test_update_event_handler_success(self):
        """Test successful event update."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "event_id": "event_123",
            "title": "Updated Meeting Title",
            "description": "Updated description"
        }
        event = {}

        mock_service = Mock()
        mock_get = Mock()
        mock_get.execute.return_value = {
            "id": "event_123",
            "summary": "Old Title",
            "description": "Old description"
        }
        mock_update = Mock()
        mock_update.execute.return_value = {
            "id": "event_123",
            "htmlLink": "https://calendar.google.com/event?eid=abc123"
        }
        mock_service.events().get.return_value = mock_get
        mock_service.events().update.return_value = mock_update

        with patch("app.integrations.simple_plugins.calendar_plugin._get_calendar_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            update_event_handler(area, params, event)

            mock_get_service.assert_called_once_with(area)
            mock_update.execute.assert_called_once()

    def test_update_event_handler_missing_event_id(self):
        """Test event update with missing event_id."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "title": "Updated Title"
        }
        event = {}

        with patch("app.integrations.simple_plugins.calendar_plugin._get_calendar_service") as mock_get_service:
            mock_get_service.return_value = Mock()

            with pytest.raises(ValueError, match="'event_id' is required to update event"):
                update_event_handler(area, params, event)

    def test_delete_event_handler_success(self):
        """Test successful event deletion."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "event_id": "event_123"
        }
        event = {}

        mock_service = Mock()
        mock_delete = Mock()
        mock_delete.execute.return_value = None
        mock_service.events().delete.return_value = mock_delete

        with patch("app.integrations.simple_plugins.calendar_plugin._get_calendar_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            delete_event_handler(area, params, event)

            mock_get_service.assert_called_once_with(area)
            mock_delete.execute.assert_called_once()

    def test_delete_event_handler_from_trigger(self):
        """Test event deletion using event_id from trigger."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {}
        event = {"calendar.event_id": "event_from_trigger"}

        mock_service = Mock()
        mock_delete = Mock()
        mock_delete.execute.return_value = None
        mock_service.events().delete.return_value = mock_delete

        with patch("app.integrations.simple_plugins.calendar_plugin._get_calendar_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            delete_event_handler(area, params, event)

            mock_get_service.assert_called_once_with(area)
            mock_delete.execute.assert_called_once()

    def test_create_all_day_event_handler_success(self):
        """Test successful all-day event creation."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "title": "All Day Conference",
            "date": "2025-10-21",
            "description": "Full day event"
        }
        event = {}

        mock_service = Mock()
        mock_insert = Mock()
        mock_insert.execute.return_value = {
            "id": "event_id_123",
            "htmlLink": "https://calendar.google.com/event?eid=abc123"
        }
        mock_service.events().insert.return_value = mock_insert

        with patch("app.integrations.simple_plugins.calendar_plugin._get_calendar_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            create_all_day_event_handler(area, params, event)

            mock_get_service.assert_called_once_with(area)
            mock_insert.execute.assert_called_once()

    def test_create_all_day_event_handler_missing_date(self):
        """Test all-day event creation with missing date."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "title": "All Day Conference"
        }
        event = {}

        with patch("app.integrations.simple_plugins.calendar_plugin._get_calendar_service") as mock_get_service:
            mock_get_service.return_value = Mock()

            with pytest.raises(ValueError, match="'date' parameter is required"):
                create_all_day_event_handler(area, params, event)

    def test_quick_add_event_handler_success(self):
        """Test successful quick add event creation."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "text": "Meeting tomorrow at 3pm"
        }
        event = {}

        mock_service = Mock()
        mock_quick_add = Mock()
        mock_quick_add.execute.return_value = {
            "id": "event_id_123",
            "htmlLink": "https://calendar.google.com/event?eid=abc123",
            "summary": "Meeting"
        }
        mock_service.events().quickAdd.return_value = mock_quick_add

        with patch("app.integrations.simple_plugins.calendar_plugin._get_calendar_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            quick_add_event_handler(area, params, event)

            mock_get_service.assert_called_once_with(area)
            mock_quick_add.execute.assert_called_once()

    def test_quick_add_event_handler_missing_text(self):
        """Test quick add event creation with missing text."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {}
        event = {}

        with patch("app.integrations.simple_plugins.calendar_plugin._get_calendar_service") as mock_get_service:
            mock_get_service.return_value = Mock()

            with pytest.raises(ValueError, match="'text' parameter is required"):
                quick_add_event_handler(area, params, event)
