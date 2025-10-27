"""Google Drive plugin for AREA - Implements file automation actions and reactions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict
from io import BytesIO

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload
from google.auth.transport.requests import Request

from app.db.session import SessionLocal
from app.services.service_connections import (
    get_service_connection_by_user_and_service,
    update_service_connection,
)
from app.schemas.service_connection import ServiceConnectionUpdate
from app.core.config import settings
from app.integrations.simple_plugins.exceptions import (
    GoogleDriveAuthError,
    GoogleDriveAPIError,
    GoogleDriveConnectionError,
)

if TYPE_CHECKING:
    from app.models.area import Area

logger = logging.getLogger("area")


def _get_drive_service(area: Area, db=None):
    """Get authenticated Google Drive API service for a user.

    Args:
        area: The Area containing user_id
        db: Database session (optional, will create if not provided)

    Returns:
        Google Drive API service object

    Raises:
        Exception: If service connection not found or authentication fails
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # Get service connection for Google Drive
        connection = get_service_connection_by_user_and_service(db, area.user_id, "google_drive")
        if not connection:
            raise GoogleDriveConnectionError("Google Drive service connection not found. Please connect your Google Drive account.")

        # Create credentials from stored tokens
        from app.core.encryption import decrypt_token
        access_token = decrypt_token(connection.encrypted_access_token)
        refresh_token = None
        if connection.encrypted_refresh_token:
            refresh_token = decrypt_token(connection.encrypted_refresh_token)

        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )

        # Auto-refresh if expired and persist new token
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                update_service_connection(
                    db,
                    str(connection.id),
                    ServiceConnectionUpdate(
                        service_name=connection.service_name,
                        access_token=creds.token,
                        expires_at=creds.expiry,
                    ),
                )
            except Exception as refresh_err:
                logger.error(
                    "Failed to refresh Google Drive token",
                    extra={
                        "user_id": str(area.user_id),
                        "area_id": str(area.id),
                        "error": str(refresh_err),
                    },
                    exc_info=True,
                )
                raise GoogleDriveAuthError("Failed to refresh Google Drive token") from refresh_err

        # Build Drive service
        service = build('drive', 'v3', credentials=creds)
        return service
    finally:
        if close_db:
            db.close()


def upload_file_handler(area: Area, params: dict, event: dict) -> None:
    """Upload a file to Google Drive.

    Args:
        area: The Area being executed
        params: Action parameters with 'file_name', 'content', optional 'folder_id', 'mime_type'
        event: Event data from trigger
    """
    try:
        # Extract parameters
        file_name = params.get("file_name")
        content = params.get("content", "")
        folder_id = params.get("folder_id")
        mime_type = params.get("mime_type", "text/plain")

        logger.info(
            "Starting Google Drive upload_file action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "file_name": file_name,
                "folder_id": folder_id,
                "mime_type": mime_type,
                "content_length": len(content) if content else 0,
            },
        )

        if not file_name:
            raise ValueError("'file_name' parameter is required for upload_file action")

        # Get Drive service
        service = _get_drive_service(area)

        # Prepare file metadata
        file_metadata = {'name': file_name}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        # Upload file
        media = MediaIoBaseUpload(
            BytesIO(content.encode('utf-8') if isinstance(content, str) else content),
            mimetype=mime_type,
            resumable=True
        )

        result = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,webViewLink,mimeType'
        ).execute()

        logger.info(
            "File uploaded successfully to Google Drive",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "file_id": result.get('id'),
                "file_name": result.get('name'),
                "file_url": result.get('webViewLink'),
                "mime_type": result.get('mimeType'),
            }
        )
    except HttpError as e:
        logger.error(
            "Google Drive API error uploading file",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise GoogleDriveAPIError(f"Failed to upload file: {e}") from e
    except Exception as e:
        logger.error(
            "Error uploading file to Google Drive",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise


def create_folder_handler(area: Area, params: dict, event: dict) -> None:
    """Create a folder in Google Drive.

    Args:
        area: The Area being executed
        params: Action parameters with 'folder_name', optional 'parent_folder_id'
        event: Event data from trigger
    """
    try:
        # Extract parameters
        folder_name = params.get("folder_name")
        parent_folder_id = params.get("parent_folder_id")

        logger.info(
            "Starting Google Drive create_folder action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "folder_name": folder_name,
                "parent_folder_id": parent_folder_id,
            },
        )

        if not folder_name:
            raise ValueError("'folder_name' parameter is required for create_folder action")

        # Get Drive service
        service = _get_drive_service(area)

        # Prepare folder metadata
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_folder_id:
            file_metadata['parents'] = [parent_folder_id]

        # Create folder
        result = service.files().create(
            body=file_metadata,
            fields='id,name,webViewLink'
        ).execute()

        logger.info(
            "Folder created successfully in Google Drive",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "folder_id": result.get('id'),
                "folder_name": result.get('name'),
                "folder_url": result.get('webViewLink'),
            }
        )
    except HttpError as e:
        logger.error(
            "Google Drive API error creating folder",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise GoogleDriveAPIError(f"Failed to create folder: {e}") from e
    except Exception as e:
        logger.error(
            "Error creating folder in Google Drive",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise


def copy_file_handler(area: Area, params: dict, event: dict) -> None:
    """Copy a file in Google Drive.

    Args:
        area: The Area being executed
        params: Action parameters with 'file_id', optional 'new_name'
        event: Event data from trigger
    """
    try:
        # Extract parameters
        file_id = params.get("file_id")
        if not file_id:
            # Try to get from event
            file_id = event.get("drive.file_id") or event.get("file_id")

        new_name = params.get("new_name")

        logger.info(
            "Starting Google Drive copy_file action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "file_id": file_id,
                "new_name": new_name,
            },
        )

        if not file_id:
            raise ValueError("'file_id' is required to copy file. Use {{drive.file_id}} from trigger.")

        # Get Drive service
        service = _get_drive_service(area)

        # Prepare copy metadata
        body = {}
        if new_name:
            body['name'] = new_name

        # Copy file
        result = service.files().copy(
            fileId=file_id,
            body=body,
            fields='id,name,webViewLink,mimeType'
        ).execute()

        logger.info(
            "File copied successfully in Google Drive",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "original_file_id": file_id,
                "new_file_id": result.get('id'),
                "new_file_name": result.get('name'),
                "new_file_url": result.get('webViewLink'),
            }
        )
    except HttpError as e:
        logger.error(
            "Google Drive API error copying file",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise GoogleDriveAPIError(f"Failed to copy file: {e}") from e
    except Exception as e:
        logger.error(
            "Error copying file in Google Drive",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise


def move_file_handler(area: Area, params: dict, event: dict) -> None:
    """Move a file to another folder in Google Drive.

    Args:
        area: The Area being executed
        params: Action parameters with 'file_id', 'destination_folder_id'
        event: Event data from trigger
    """
    try:
        # Extract parameters
        file_id = params.get("file_id")
        if not file_id:
            # Try to get from event
            file_id = event.get("drive.file_id") or event.get("file_id")

        destination_folder_id = params.get("destination_folder_id")

        logger.info(
            "Starting Google Drive move_file action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "file_id": file_id,
                "destination_folder_id": destination_folder_id,
            },
        )

        if not file_id:
            raise ValueError("'file_id' is required to move file. Use {{drive.file_id}} from trigger.")
        if not destination_folder_id:
            raise ValueError("'destination_folder_id' parameter is required for move_file action")

        # Get Drive service
        service = _get_drive_service(area)

        # Retrieve the existing parents to remove
        file = service.files().get(fileId=file_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents', []))

        # Move the file to the new folder
        result = service.files().update(
            fileId=file_id,
            addParents=destination_folder_id,
            removeParents=previous_parents,
            fields='id,name,parents,webViewLink'
        ).execute()

        logger.info(
            "File moved successfully in Google Drive",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "file_id": result.get('id'),
                "file_name": result.get('name'),
                "new_parents": result.get('parents'),
                "file_url": result.get('webViewLink'),
            }
        )
    except HttpError as e:
        logger.error(
            "Google Drive API error moving file",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise GoogleDriveAPIError(f"Failed to move file: {e}") from e
    except Exception as e:
        logger.error(
            "Error moving file in Google Drive",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise


def delete_file_handler(area: Area, params: dict, event: dict) -> None:
    """Delete (trash) a file in Google Drive.

    Args:
        area: The Area being executed
        params: Action parameters with 'file_id'
        event: Event data from trigger
    """
    try:
        # Extract parameters
        file_id = params.get("file_id")
        if not file_id:
            # Try to get from event
            file_id = event.get("drive.file_id") or event.get("file_id")

        logger.info(
            "Starting Google Drive delete_file action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "file_id": file_id,
            },
        )

        if not file_id:
            raise ValueError("'file_id' is required to delete file. Use {{drive.file_id}} from trigger.")

        # Get Drive service
        service = _get_drive_service(area)

        # Move file to trash (soft delete)
        result = service.files().update(
            fileId=file_id,
            body={'trashed': True},
            fields='id,name,trashed'
        ).execute()

        logger.info(
            "File deleted (trashed) successfully in Google Drive",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "file_id": result.get('id'),
                "file_name": result.get('name'),
                "trashed": result.get('trashed'),
            }
        )
    except HttpError as e:
        logger.error(
            "Google Drive API error deleting file",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise GoogleDriveAPIError(f"Failed to delete file: {e}") from e
    except Exception as e:
        logger.error(
            "Error deleting file in Google Drive",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise


__all__ = [
    "upload_file_handler",
    "create_folder_handler",
    "copy_file_handler",
    "move_file_handler",
    "delete_file_handler",
]
