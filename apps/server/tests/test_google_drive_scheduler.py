"""Tests for Google Drive scheduler functionality."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

import pytest
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

from app.integrations.simple_plugins.google_drive_scheduler import (
    _get_drive_service,
    _get_start_page_token,
    _fetch_changes,
    _fetch_files_in_folder,
    start_google_drive_scheduler,
    stop_google_drive_scheduler,
    is_google_drive_scheduler_running,
    clear_google_drive_seen_state,
)


class TestGoogleDriveScheduler:
    """Test Google Drive scheduler functionality."""

    def test_get_drive_service_success(self):
        """Test successful Drive service creation."""
        user_id = "test-user-id"
        mock_db = Mock()
        mock_connection = Mock()
        mock_connection.encrypted_access_token = b"encrypted_access_token"
        mock_connection.encrypted_refresh_token = b"encrypted_refresh_token"

        with patch("app.integrations.simple_plugins.google_drive_scheduler.get_service_connection_by_user_and_service") as mock_get_conn, \
             patch("app.integrations.simple_plugins.google_drive_scheduler.decrypt_token") as mock_decrypt, \
             patch("app.integrations.simple_plugins.google_drive_scheduler.build") as mock_build, \
             patch("app.integrations.simple_plugins.google_drive_scheduler.Credentials") as mock_credentials:

            mock_get_conn.return_value = mock_connection
            mock_decrypt.side_effect = lambda x: x.decode() if isinstance(x, bytes) else str(x)

            mock_creds = Mock()
            mock_creds.expired = False
            mock_creds.valid = True
            mock_creds.refresh_token = "decrypted_refresh_token"
            mock_credentials.return_value = mock_creds

            mock_service = Mock()
            mock_build.return_value = mock_service

            result = _get_drive_service(user_id, mock_db)

            assert result == mock_service
            mock_get_conn.assert_called_once_with(mock_db, user_id, "google_drive")

    def test_get_drive_service_no_connection(self):
        """Test Drive service creation when no connection exists."""
        user_id = "test-user-id"
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.google_drive_scheduler.get_service_connection_by_user_and_service") as mock_get_conn:
            mock_get_conn.return_value = None

            result = _get_drive_service(user_id, mock_db)

            assert result is None

    def test_get_drive_service_token_refresh(self):
        """Test Drive service creation with token refresh."""
        user_id = "test-user-id"
        mock_db = Mock()
        mock_connection = Mock()
        mock_connection.id = "connection-id"
        mock_connection.service_name = "google_drive"
        mock_connection.encrypted_access_token = b"encrypted_access_token"
        mock_connection.encrypted_refresh_token = b"encrypted_refresh_token"

        with patch("app.integrations.simple_plugins.google_drive_scheduler.get_service_connection_by_user_and_service") as mock_get_conn, \
             patch("app.integrations.simple_plugins.google_drive_scheduler.decrypt_token") as mock_decrypt, \
             patch("app.integrations.simple_plugins.google_drive_scheduler.build") as mock_build, \
             patch("app.integrations.simple_plugins.google_drive_scheduler.Credentials") as mock_credentials, \
             patch("app.integrations.simple_plugins.google_drive_scheduler.update_service_connection") as mock_update, \
             patch("app.integrations.simple_plugins.google_drive_scheduler.Request") as mock_request:

            mock_get_conn.return_value = mock_connection
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

            result = _get_drive_service(user_id, mock_db)

            assert result == mock_service
            mock_creds.refresh.assert_called_once()
            mock_update.assert_called_once()

    def test_get_drive_service_refresh_error(self):
        """Test Drive service creation when token refresh fails."""
        user_id = "test-user-id"
        mock_db = Mock()
        mock_connection = Mock()
        mock_connection.id = "connection-id"
        mock_connection.service_name = "google_drive"
        mock_connection.encrypted_access_token = b"encrypted_access_token"
        mock_connection.encrypted_refresh_token = b"encrypted_refresh_token"

        with patch("app.integrations.simple_plugins.google_drive_scheduler.get_service_connection_by_user_and_service") as mock_get_conn, \
             patch("app.integrations.simple_plugins.google_drive_scheduler.decrypt_token") as mock_decrypt, \
             patch("app.integrations.simple_plugins.google_drive_scheduler.Credentials") as mock_credentials:

            mock_get_conn.return_value = mock_connection
            mock_decrypt.side_effect = lambda x: x.decode() if isinstance(x, bytes) else str(x)

            # Mock credentials that fail to refresh
            mock_creds = Mock()
            mock_creds.expired = True
            mock_creds.refresh_token = "decrypted_refresh_token"
            mock_creds.refresh.side_effect = RefreshError("Token expired")
            mock_credentials.return_value = mock_creds

            result = _get_drive_service(user_id, mock_db)

            assert result is None

    def test_get_start_page_token_success(self):
        """Test successful page token retrieval."""
        mock_service = Mock()
        mock_response = {"startPageToken": "token123"}
        mock_service.changes().getStartPageToken().execute.return_value = mock_response

        result = _get_start_page_token(mock_service)

        assert result == "token123"

    def test_get_start_page_token_api_error(self):
        """Test page token retrieval with API error."""
        mock_service = Mock()
        mock_error = HttpError(Mock(status=403), b'{"error": "Permission denied"}')
        mock_service.changes().getStartPageToken().execute.side_effect = mock_error

        result = _get_start_page_token(mock_service)

        assert result is None

    def test_fetch_changes_success(self):
        """Test successful changes fetch."""
        mock_service = Mock()
        mock_changes = [
            {
                "fileId": "file123",
                "file": {
                    "id": "file123",
                    "name": "test.txt",
                    "mimeType": "text/plain",
                    "trashed": False,
                    "createdTime": "2024-01-01T00:00:00Z",
                    "modifiedTime": "2024-01-01T00:00:00Z",
                    "webViewLink": "https://drive.google.com/file/d/file123",
                    "size": 1024
                },
                "removed": False,
                "time": "2024-01-01T00:00:00Z"
            }
        ]
        mock_response = {
            "changes": mock_changes,
            "newStartPageToken": "token456"
        }
        mock_service.changes().list().execute.return_value = mock_response

        changes, next_token = _fetch_changes(mock_service, "token123")

        assert len(changes) == 1
        assert changes[0]["fileId"] == "file123"
        assert next_token == "token456"

    def test_fetch_changes_with_next_page(self):
        """Test changes fetch with pagination."""
        mock_service = Mock()
        mock_changes = [{"fileId": "file123"}]
        mock_response = {
            "changes": mock_changes,
            "nextPageToken": "token456"
        }
        mock_service.changes().list().execute.return_value = mock_response

        changes, next_token = _fetch_changes(mock_service, "token123")

        assert len(changes) == 1
        assert next_token == "token456"

    def test_fetch_changes_api_error(self):
        """Test changes fetch with API error."""
        mock_service = Mock()
        mock_error = HttpError(Mock(status=500), b'{"error": "Internal error"}')
        mock_service.changes().list().execute.side_effect = mock_error

        changes, next_token = _fetch_changes(mock_service, "token123")

        assert changes == []
        assert next_token is None

    def test_fetch_changes_refresh_error(self):
        """Test changes fetch with refresh error."""
        mock_service = Mock()
        mock_service.changes().list().execute.side_effect = RefreshError("Token expired")

        changes, next_token = _fetch_changes(mock_service, "token123")

        assert changes == []
        assert next_token is None

    def test_fetch_files_in_folder_success(self):
        """Test successful folder files fetch."""
        mock_service = Mock()
        mock_files = [
            {
                "id": "file123",
                "name": "test.txt",
                "mimeType": "text/plain",
                "createdTime": "2024-01-01T00:00:00Z",
                "modifiedTime": "2024-01-01T00:00:00Z"
            }
        ]
        mock_response = {"files": mock_files}
        mock_service.files().list().execute.return_value = mock_response

        result = _fetch_files_in_folder(mock_service, "folder123")

        assert len(result) == 1
        assert result[0]["id"] == "file123"

    def test_fetch_files_in_folder_empty(self):
        """Test folder files fetch with no files."""
        mock_service = Mock()
        mock_response = {"files": []}
        mock_service.files().list().execute.return_value = mock_response

        result = _fetch_files_in_folder(mock_service, "folder123")

        assert result == []

    def test_fetch_files_in_folder_api_error(self):
        """Test folder files fetch with API error."""
        mock_service = Mock()
        mock_error = HttpError(Mock(status=404), b'{"error": "Folder not found"}')
        mock_service.files().list().execute.side_effect = mock_error

        result = _fetch_files_in_folder(mock_service, "folder123")

        assert result == []

    def test_clear_google_drive_seen_state(self):
        """Test clearing seen state."""
        # This function clears internal state dictionaries
        # Just test it doesn't raise exceptions
        clear_google_drive_seen_state()
        # If it runs without error, test passes

    def test_is_google_drive_scheduler_running_false(self):
        """Test scheduler running check when not running."""
        with patch("app.integrations.simple_plugins.google_drive_scheduler._google_drive_scheduler_task", None):
            assert is_google_drive_scheduler_running() is False

    def test_is_google_drive_scheduler_running_true(self):
        """Test scheduler running check when running."""
        mock_task = Mock()
        mock_task.done.return_value = False

        with patch("app.integrations.simple_plugins.google_drive_scheduler._google_drive_scheduler_task", mock_task):
            assert is_google_drive_scheduler_running() is True

    def test_is_google_drive_scheduler_running_done_task(self):
        """Test scheduler running check with done task."""
        mock_task = Mock()
        mock_task.done.return_value = True

        with patch("app.integrations.simple_plugins.google_drive_scheduler._google_drive_scheduler_task", mock_task):
            assert is_google_drive_scheduler_running() is False

    @pytest.mark.asyncio
    async def test_start_google_drive_scheduler(self):
        """Test starting the scheduler."""
        with patch("app.integrations.simple_plugins.google_drive_scheduler._google_drive_scheduler_task", None):
            # Mock the task creation
            mock_task = Mock()
            with patch("asyncio.create_task", return_value=mock_task):
                start_google_drive_scheduler()
                # Scheduler should be started
                # This is a simple test - full async testing would require more setup

    def test_stop_google_drive_scheduler_not_running(self):
        """Test stopping scheduler when not running."""
        with patch("app.integrations.simple_plugins.google_drive_scheduler._google_drive_scheduler_task", None):
            stop_google_drive_scheduler()
            # Should complete without error

    def test_stop_google_drive_scheduler_running(self):
        """Test stopping running scheduler."""
        mock_task = Mock()
        mock_task.done.return_value = False
        mock_task.cancel = Mock()

        with patch("app.integrations.simple_plugins.google_drive_scheduler._google_drive_scheduler_task", mock_task):
            stop_google_drive_scheduler()
            mock_task.cancel.assert_called_once()
