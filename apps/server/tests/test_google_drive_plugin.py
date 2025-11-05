"""Tests for Google Drive plugin handlers."""

from __future__ import annotations

from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

import pytest
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

from app.integrations.simple_plugins.google_drive_plugin import (
    _get_drive_service,
    upload_file_handler,
    create_folder_handler,
    copy_file_handler,
    move_file_handler,
    delete_file_handler,
)
from app.integrations.simple_plugins.exceptions import (
    GoogleDriveAuthError,
    GoogleDriveAPIError,
    GoogleDriveConnectionError,
)


class TestGoogleDrivePlugin:
    """Test Google Drive plugin functionality."""

    def test_get_drive_service_success(self):
        """Test successful Google Drive service creation."""
        # Mock area
        area = Mock()
        area.user_id = "test-user-id"
        area.id = "test-area-id"

        # Mock database and service connection
        mock_db = Mock()
        mock_connection = Mock()
        mock_connection.encrypted_access_token = b"encrypted_access_token"
        mock_connection.encrypted_refresh_token = b"encrypted_refresh_token"

        with patch("app.integrations.simple_plugins.google_drive_plugin.get_service_connection_by_user_and_service") as mock_get_conn, \
             patch("app.core.encryption.decrypt_token") as mock_decrypt, \
             patch("app.integrations.simple_plugins.google_drive_plugin.build") as mock_build, \
             patch("app.integrations.simple_plugins.google_drive_plugin.Credentials") as mock_credentials:

            mock_get_conn.return_value = mock_connection
            mock_decrypt.side_effect = ["decrypted_access_token", "decrypted_refresh_token"]

            mock_creds = Mock()
            mock_creds.expired = False
            mock_creds.refresh_token = "decrypted_refresh_token"
            mock_credentials.return_value = mock_creds

            mock_service = Mock()
            mock_build.return_value = mock_service

            result = _get_drive_service(area, mock_db)

            assert result == mock_service
            mock_get_conn.assert_called_once_with(mock_db, "test-user-id", "google_drive")

    def test_get_drive_service_no_connection(self):
        """Test Drive service creation when no connection exists."""
        area = Mock()
        area.user_id = "test-user-id"
        area.id = "test-area-id"
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.google_drive_plugin.get_service_connection_by_user_and_service") as mock_get_conn:
            mock_get_conn.return_value = None

            with pytest.raises(GoogleDriveConnectionError, match="Google Drive service connection not found"):
                _get_drive_service(area, mock_db)

    def test_get_drive_service_token_refresh(self):
        """Test Drive service creation with token refresh."""
        area = Mock()
        area.user_id = "test-user-id"
        area.id = "test-area-id"
        mock_db = Mock()
        mock_connection = Mock()
        mock_connection.id = "connection-id"
        mock_connection.service_name = "google_drive"
        mock_connection.encrypted_access_token = b"encrypted_access_token"
        mock_connection.encrypted_refresh_token = b"encrypted_refresh_token"

        with patch("app.integrations.simple_plugins.google_drive_plugin.get_service_connection_by_user_and_service") as mock_get_conn, \
             patch("app.core.encryption.decrypt_token") as mock_decrypt, \
             patch("app.integrations.simple_plugins.google_drive_plugin.build") as mock_build, \
             patch("app.integrations.simple_plugins.google_drive_plugin.Credentials") as mock_credentials, \
             patch("app.integrations.simple_plugins.google_drive_plugin.update_service_connection") as mock_update, \
             patch("app.integrations.simple_plugins.google_drive_plugin.Request") as mock_request:

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

            result = _get_drive_service(area, mock_db)

            assert result == mock_service
            mock_creds.refresh.assert_called_once()
            mock_update.assert_called_once()

    def test_get_drive_service_token_refresh_failure(self):
        """Test Drive service creation when token refresh fails."""
        area = Mock()
        area.user_id = "test-user-id"
        area.id = "test-area-id"
        mock_db = Mock()
        mock_connection = Mock()
        mock_connection.id = "connection-id"
        mock_connection.service_name = "google_drive"
        mock_connection.encrypted_access_token = b"encrypted_access_token"
        mock_connection.encrypted_refresh_token = b"encrypted_refresh_token"

        with patch("app.integrations.simple_plugins.google_drive_plugin.get_service_connection_by_user_and_service") as mock_get_conn, \
             patch("app.core.encryption.decrypt_token") as mock_decrypt, \
             patch("app.integrations.simple_plugins.google_drive_plugin.Credentials") as mock_credentials:

            mock_get_conn.return_value = mock_connection
            mock_decrypt.side_effect = ["decrypted_access_token", "decrypted_refresh_token"]

            # Mock credentials that fail to refresh
            mock_creds = Mock()
            mock_creds.expired = True
            mock_creds.refresh_token = "decrypted_refresh_token"
            mock_creds.refresh.side_effect = Exception("Refresh failed")
            mock_credentials.return_value = mock_creds

            with pytest.raises(GoogleDriveAuthError, match="Failed to refresh Google Drive token"):
                _get_drive_service(area, mock_db)

    def test_upload_file_handler_success(self):
        """Test successful file upload."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "file_name": "test.txt",
            "file_content": "Test content",
            "folder_id": "folder123",
            "mime_type": "text/plain"
        }
        event = {}

        mock_service = Mock()
        mock_create = Mock()
        mock_create.execute.return_value = {
            "id": "file123",
            "name": "test.txt",
            "webViewLink": "https://drive.google.com/file/d/file123",
            "mimeType": "text/plain"
        }
        mock_service.files().create.return_value = mock_create

        with patch("app.integrations.simple_plugins.google_drive_plugin._get_drive_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            upload_file_handler(area, params, event)

            mock_get_service.assert_called_once_with(area)
            mock_create.execute.assert_called_once()

    def test_upload_file_handler_missing_filename(self):
        """Test file upload with missing file name."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {"file_content": "Test content"}  # Missing file_name
        event = {}

        with patch("app.integrations.simple_plugins.google_drive_plugin._get_drive_service") as mock_get_service:
            mock_get_service.return_value = Mock()

            with pytest.raises(ValueError, match="'file_name' parameter is required"):
                upload_file_handler(area, params, event)

    def test_upload_file_handler_api_error(self):
        """Test file upload with API error."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "file_name": "test.txt",
            "file_content": "Test content"
        }
        event = {}

        mock_service = Mock()
        mock_error = HttpError(Mock(status=403), b'{"error": "Permission denied"}')
        mock_service.files().create().execute.side_effect = mock_error

        with patch("app.integrations.simple_plugins.google_drive_plugin._get_drive_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            with pytest.raises(GoogleDriveAPIError, match="Failed to upload file"):
                upload_file_handler(area, params, event)

    def test_create_folder_handler_success(self):
        """Test successful folder creation."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "folder_name": "New Folder",
            "parent_folder_id": "parent123"
        }
        event = {}

        mock_service = Mock()
        mock_create = Mock()
        mock_create.execute.return_value = {
            "id": "folder456",
            "name": "New Folder",
            "webViewLink": "https://drive.google.com/drive/folders/folder456"
        }
        mock_service.files().create.return_value = mock_create

        with patch("app.integrations.simple_plugins.google_drive_plugin._get_drive_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            create_folder_handler(area, params, event)

            mock_get_service.assert_called_once_with(area)
            mock_create.execute.assert_called_once()

    def test_create_folder_handler_missing_name(self):
        """Test folder creation with missing folder name."""
        area = Mock()
        params = {}
        event = {}

        with patch("app.integrations.simple_plugins.google_drive_plugin._get_drive_service") as mock_get_service:
            mock_get_service.return_value = Mock()

            with pytest.raises(ValueError, match="'folder_name' parameter is required"):
                create_folder_handler(area, params, event)

    def test_copy_file_handler_success(self):
        """Test successful file copy."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "file_id": "file123",
            "new_name": "Copy of file"
        }
        event = {}

        mock_service = Mock()
        mock_copy = Mock()
        mock_copy.execute.return_value = {
            "id": "file789",
            "name": "Copy of file",
            "webViewLink": "https://drive.google.com/file/d/file789",
            "mimeType": "text/plain"
        }
        mock_service.files().copy.return_value = mock_copy

        with patch("app.integrations.simple_plugins.google_drive_plugin._get_drive_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            copy_file_handler(area, params, event)

            mock_get_service.assert_called_once_with(area)
            mock_copy.execute.assert_called_once()

    def test_copy_file_handler_from_event(self):
        """Test file copy using file_id from event."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {}  # No file_id in params
        event = {"drive.file_id": "file123"}

        mock_service = MagicMock()
        mock_copy = Mock()
        mock_copy.execute.return_value = {
            "id": "file789",
            "name": "Copy of file",
            "webViewLink": "https://drive.google.com/file/d/file789",
            "mimeType": "text/plain"
        }
        mock_service.files().copy.return_value = mock_copy

        with patch("app.integrations.simple_plugins.google_drive_plugin._get_drive_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            copy_file_handler(area, params, event)

            mock_copy.execute.assert_called_once()

    def test_copy_file_handler_missing_file_id(self):
        """Test file copy with missing file_id."""
        area = Mock()
        area.id = "test-area-id"
        params = {}
        event = {}

        with patch("app.integrations.simple_plugins.google_drive_plugin._get_drive_service") as mock_get_service:
            mock_get_service.return_value = Mock()

            with pytest.raises(ValueError, match="'file_id' is required"):
                copy_file_handler(area, params, event)

    def test_move_file_handler_success(self):
        """Test successful file move."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {
            "file_id": "file123",
            "destination_folder_id": "folder456"
        }
        event = {}

        mock_service = Mock()
        mock_get = Mock()
        mock_get.execute.return_value = {"parents": ["oldparent"]}
        mock_service.files().get.return_value = mock_get

        mock_update = Mock()
        mock_update.execute.return_value = {
            "id": "file123",
            "name": "moved file",
            "parents": ["folder456"],
            "webViewLink": "https://drive.google.com/file/d/file123"
        }
        mock_service.files().update.return_value = mock_update

        with patch("app.integrations.simple_plugins.google_drive_plugin._get_drive_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            move_file_handler(area, params, event)

            mock_get_service.assert_called_once_with(area)
            mock_get.execute.assert_called_once()
            mock_update.execute.assert_called_once()

    def test_move_file_handler_missing_destination(self):
        """Test file move with missing destination folder."""
        area = Mock()
        params = {"file_id": "file123"}
        event = {}

        with patch("app.integrations.simple_plugins.google_drive_plugin._get_drive_service") as mock_get_service:
            mock_get_service.return_value = Mock()

            with pytest.raises(ValueError, match="'destination_folder_id' parameter is required"):
                move_file_handler(area, params, event)

    def test_delete_file_handler_success(self):
        """Test successful file deletion."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {"file_id": "file123"}
        event = {}

        mock_service = Mock()
        mock_update = Mock()
        mock_update.execute.return_value = {
            "id": "file123",
            "name": "deleted file",
            "trashed": True
        }
        mock_service.files().update.return_value = mock_update

        with patch("app.integrations.simple_plugins.google_drive_plugin._get_drive_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            delete_file_handler(area, params, event)

            mock_get_service.assert_called_once_with(area)
            mock_update.execute.assert_called_once()

    def test_delete_file_handler_from_event(self):
        """Test file deletion using file_id from event."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Area"

        params = {}
        event = {"drive.file_id": "file123"}

        mock_service = MagicMock()
        mock_update = Mock()
        mock_update.execute.return_value = {
            "id": "file123",
            "name": "deleted file",
            "trashed": True
        }
        mock_service.files().update.return_value = mock_update

        with patch("app.integrations.simple_plugins.google_drive_plugin._get_drive_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            delete_file_handler(area, params, event)

            mock_update.execute.assert_called_once()

    def test_delete_file_handler_missing_file_id(self):
        """Test file deletion with missing file_id."""
        area = Mock()
        params = {}
        event = {}

        with patch("app.integrations.simple_plugins.google_drive_plugin._get_drive_service") as mock_get_service:
            mock_get_service.return_value = Mock()

            with pytest.raises(ValueError, match="'file_id' is required"):
                delete_file_handler(area, params, event)
