"""Google Drive polling scheduler for trigger-based automation."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

from app.core.encryption import decrypt_token
from app.core.config import settings
from app.integrations.variable_extractor import extract_google_drive_variables
from app.models.area import Area
from app.schemas.execution_log import ExecutionLogCreate
from app.services.execution_logs import create_execution_log
from app.services.service_connections import (
    get_service_connection_by_user_and_service,
    update_service_connection,
)
from app.schemas.service_connection import ServiceConnectionUpdate
from app.services.step_executor import execute_area

logger = logging.getLogger("area")

# In-memory storage for tracking changes per user
_last_page_tokens: Dict[str, str] = {}
_last_seen_files: Dict[str, set[str]] = {}
_google_drive_scheduler_task: asyncio.Task | None = None


def _get_drive_service(user_id, db: Session):
    """Get authenticated Google Drive service for a user.

    Args:
        user_id: User UUID
        db: Database session

    Returns:
        Drive service object or None if connection not found
    """
    try:
        connection = get_service_connection_by_user_and_service(db, user_id, "google_drive")
        if not connection:
            return None

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

        # Refresh if needed and persist new access token
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Persist updated access token and expiry
                update_service_connection(
                    db,
                    str(connection.id),
                    ServiceConnectionUpdate(
                        service_name=connection.service_name,
                        access_token=creds.token,
                        expires_at=creds.expiry,
                    ),
                )
            except RefreshError as refresh_err:
                logger.warning(
                    f"Google Drive token expired or revoked for user {user_id}. "
                    f"User needs to reconnect their Google Drive account."
                )
                return None
            except Exception as refresh_err:
                logger.error(f"Failed to refresh Google Drive token: {refresh_err}")
                return None

        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        logger.error(f"Failed to get Google Drive service: {e}", exc_info=True)
        return None


def _get_start_page_token(service) -> str | None:
    """Get the start page token for change tracking.

    Args:
        service: Google Drive API service

    Returns:
        Page token string or None
    """
    try:
        response = service.changes().getStartPageToken().execute()
        return response.get('startPageToken')
    except HttpError as e:
        logger.error(f"Failed to get start page token: {e}")
        return None


def _fetch_changes(service, page_token: str) -> tuple[list[dict], str | None]:
    """Fetch changes from Google Drive API.

    Args:
        service: Google Drive API service
        page_token: Page token to start from

    Returns:
        Tuple of (list of changes, next page token)
    """
    try:
        response = service.changes().list(
            pageToken=page_token,
            spaces='drive',
            fields='changes(file(id,name,mimeType,trashed,createdTime,modifiedTime,owners,webViewLink,parents,shared,size),fileId,removed,time),newStartPageToken,nextPageToken',
            pageSize=100
        ).execute()

        changes = response.get('changes', [])
        new_start_page_token = response.get('newStartPageToken')
        next_page_token = response.get('nextPageToken')

        return changes, new_start_page_token or next_page_token
    except RefreshError:
        # Token expired/revoked - already logged in _get_drive_service
        return [], None
    except HttpError as e:
        logger.error(f"Google Drive API error fetching changes: {e}", exc_info=True)
        return [], None


def _fetch_files_in_folder(service, folder_id: str) -> list[dict]:
    """Fetch files in a specific folder.

    Args:
        service: Google Drive API service
        folder_id: Folder ID to query

    Returns:
        List of file objects
    """
    try:
        query = f"'{folder_id}' in parents and trashed = false"
        response = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id,name,mimeType,createdTime,modifiedTime,owners,webViewLink,parents,size)',
            pageSize=20,
            orderBy='createdTime desc'
        ).execute()

        return response.get('files', [])
    except HttpError as e:
        logger.error(f"Failed to fetch files in folder: {e}")
        return []


def _fetch_shared_files(service) -> list[dict]:
    """Fetch files shared with the user.

    Args:
        service: Google Drive API service

    Returns:
        List of file objects
    """
    try:
        query = "sharedWithMe = true and trashed = false"
        response = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id,name,mimeType,createdTime,modifiedTime,owners,webViewLink,shared,size)',
            pageSize=20,
            orderBy='sharedWithMeTime desc'
        ).execute()

        return response.get('files', [])
    except HttpError as e:
        logger.error(f"Failed to fetch shared files: {e}")
        return []


def _extract_file_data(file_obj: dict) -> dict:
    """Extract relevant data from Drive file object.

    Args:
        file_obj: File object from Drive API

    Returns:
        Dictionary with extracted file data
    """
    return {
        'id': file_obj.get('id'),
        'name': file_obj.get('name'),
        'mimeType': file_obj.get('mimeType'),
        'webViewLink': file_obj.get('webViewLink'),
        'createdTime': file_obj.get('createdTime'),
        'modifiedTime': file_obj.get('modifiedTime'),
        'trashed': file_obj.get('trashed', False),
        'shared': file_obj.get('shared', False),
        'size': file_obj.get('size'),
        'owners': file_obj.get('owners', []),
        'parents': file_obj.get('parents', []),
    }


def _fetch_due_google_drive_areas(db: Session) -> list[Area]:
    """Fetch all enabled areas with Google Drive triggers.

    Args:
        db: Database session

    Returns:
        List of Area objects
    """
    return (
        db.query(Area)
        .filter(
            Area.enabled == True,  # noqa: E712
            Area.trigger_service == "google_drive",
        )
        .all()
    )


async def google_drive_scheduler_task() -> None:
    """Background task that polls Google Drive for changes based on AREA triggers."""
    from app.db.session import SessionLocal

    logger.info("Starting Google Drive polling scheduler task")

    while True:
        try:
            # Poll at configurable interval (default: 60 seconds)
            await asyncio.sleep(settings.google_drive_poll_interval_seconds)

            now = datetime.now(timezone.utc)

            # Fetch all enabled Google Drive areas using a scoped session
            with SessionLocal() as db:
                areas = await asyncio.to_thread(_fetch_due_google_drive_areas, db)

                logger.info(
                    "Google Drive scheduler tick",
                    extra={
                        "utc_now": now.isoformat(),
                        "areas_count": len(areas),
                    },
                )

            # Process each area with its own scoped session
            for area in areas:
                area_id_str = str(area.id)
                user_id_str = str(area.user_id)

                # Initialize tracking for this area
                if area_id_str not in _last_seen_files:
                    _last_seen_files[area_id_str] = set()

                try:
                    # Use scoped session for this area's processing
                    with SessionLocal() as db:
                        # Get Drive service for user
                        service = await asyncio.to_thread(_get_drive_service, area.user_id, db)
                        if not service:
                            logger.warning(
                                f"Google Drive service not available for area {area_id_str}, skipping"
                            )
                            continue

                        # Process based on trigger action
                        await _process_area_trigger(db, area, service, now)

                except RefreshError as e:
                    # Token expired/revoked - show clean warning
                    logger.warning(
                        f"Google Drive area {area_id_str} skipped: token expired or revoked. "
                        f"User needs to reconnect Google Drive account."
                    )
                except Exception as e:
                    logger.error(
                        "Error processing Google Drive area",
                        extra={
                            "area_id": area_id_str,
                            "error": str(e),
                        },
                        exc_info=True,
                    )

        except asyncio.CancelledError:
            logger.info("Google Drive scheduler task cancelled, shutting down gracefully")
            break

        except Exception as e:
            logger.error("Google Drive scheduler task error", extra={"error": str(e)}, exc_info=True)
            await asyncio.sleep(30)  # Back off on error

    logger.info("Google Drive scheduler task stopped")


async def _process_area_trigger(db: Session, area: Area, service, now: datetime) -> None:
    """Process a specific area's trigger logic.

    Args:
        db: Database session
        area: Area to process
        service: Google Drive service
        now: Current timestamp
    """
    area_id_str = str(area.id)
    user_id_str = str(area.user_id)
    trigger_action = area.trigger_action
    params = area.trigger_params or {}

    # Route to specific trigger handler
    if trigger_action == "new_file":
        await _handle_new_file_trigger(db, area, service, now)
    elif trigger_action == "file_modified":
        await _handle_file_modified_trigger(db, area, service, now)
    elif trigger_action == "file_in_folder":
        await _handle_file_in_folder_trigger(db, area, service, now, params)
    elif trigger_action == "file_shared_with_me":
        await _handle_file_shared_trigger(db, area, service, now)
    elif trigger_action == "file_trashed":
        await _handle_file_trashed_trigger(db, area, service, now)
    else:
        logger.warning(
            f"Unknown Google Drive trigger action: {trigger_action} for area {area_id_str}"
        )


async def _handle_new_file_trigger(db: Session, area: Area, service, now: datetime) -> None:
    """Handle new_file trigger using Changes API."""
    user_id_str = str(area.user_id)
    area_id_str = str(area.id)

    # Initialize page token if not exists
    if user_id_str not in _last_page_tokens:
        token = await asyncio.to_thread(_get_start_page_token, service)
        if token:
            _last_page_tokens[user_id_str] = token
            logger.info(f"Initialized page token for user {user_id_str}")
        return

    # Fetch changes
    changes, new_token = await asyncio.to_thread(
        _fetch_changes, service, _last_page_tokens[user_id_str]
    )

    if new_token:
        _last_page_tokens[user_id_str] = new_token

    # Filter for new files (not removed, not trashed)
    new_files = [
        change['file'] for change in changes
        if not change.get('removed', False)
        and 'file' in change
        and not change['file'].get('trashed', False)
        and change['file']['id'] not in _last_seen_files[area_id_str]
    ]

    # Process each new file
    for file_obj in new_files:
        file_data = _extract_file_data(file_obj)
        await _execute_drive_trigger(db, area, file_data, now)
        _last_seen_files[area_id_str].add(file_obj['id'])


async def _handle_file_modified_trigger(db: Session, area: Area, service, now: datetime) -> None:
    """Handle file_modified trigger using Changes API."""
    user_id_str = str(area.user_id)
    area_id_str = str(area.id)

    # Initialize page token if not exists
    if user_id_str not in _last_page_tokens:
        token = await asyncio.to_thread(_get_start_page_token, service)
        if token:
            _last_page_tokens[user_id_str] = token
        return

    # Fetch changes
    changes, new_token = await asyncio.to_thread(
        _fetch_changes, service, _last_page_tokens[user_id_str]
    )

    if new_token:
        _last_page_tokens[user_id_str] = new_token

    # Filter for modified files (existing files with changes)
    modified_files = [
        change['file'] for change in changes
        if not change.get('removed', False)
        and 'file' in change
        and not change['file'].get('trashed', False)
        and change['file']['id'] in _last_seen_files[area_id_str]
    ]

    # Process each modified file
    for file_obj in modified_files:
        file_data = _extract_file_data(file_obj)
        await _execute_drive_trigger(db, area, file_data, now)


async def _handle_file_in_folder_trigger(db: Session, area: Area, service, now: datetime, params: dict) -> None:
    """Handle file_in_folder trigger."""
    area_id_str = str(area.id)
    folder_id = params.get("folder_id")

    if not folder_id:
        logger.warning(f"No folder_id specified for file_in_folder trigger in area {area_id_str}")
        return

    # Fetch files in folder
    files = await asyncio.to_thread(_fetch_files_in_folder, service, folder_id)

    # Filter for new files
    new_files = [f for f in files if f['id'] not in _last_seen_files[area_id_str]]

    # Process each new file
    for file_obj in new_files:
        file_data = _extract_file_data(file_obj)
        await _execute_drive_trigger(db, area, file_data, now)
        _last_seen_files[area_id_str].add(file_obj['id'])


async def _handle_file_shared_trigger(db: Session, area: Area, service, now: datetime) -> None:
    """Handle file_shared_with_me trigger."""
    area_id_str = str(area.id)

    # Fetch shared files
    files = await asyncio.to_thread(_fetch_shared_files, service)

    # Filter for new shared files
    new_files = [f for f in files if f['id'] not in _last_seen_files[area_id_str]]

    # Process each new shared file
    for file_obj in new_files:
        file_data = _extract_file_data(file_obj)
        await _execute_drive_trigger(db, area, file_data, now)
        _last_seen_files[area_id_str].add(file_obj['id'])


async def _handle_file_trashed_trigger(db: Session, area: Area, service, now: datetime) -> None:
    """Handle file_trashed trigger using Changes API."""
    user_id_str = str(area.user_id)

    # Initialize page token if not exists
    if user_id_str not in _last_page_tokens:
        token = await asyncio.to_thread(_get_start_page_token, service)
        if token:
            _last_page_tokens[user_id_str] = token
        return

    # Fetch changes
    changes, new_token = await asyncio.to_thread(
        _fetch_changes, service, _last_page_tokens[user_id_str]
    )

    if new_token:
        _last_page_tokens[user_id_str] = new_token

    # Filter for trashed files
    trashed_files = [
        change['file'] for change in changes
        if not change.get('removed', False)
        and 'file' in change
        and change['file'].get('trashed', False)
    ]

    # Process each trashed file
    for file_obj in trashed_files:
        file_data = _extract_file_data(file_obj)
        await _execute_drive_trigger(db, area, file_data, now)


async def _execute_drive_trigger(db: Session, area: Area, file_data: dict, now: datetime) -> None:
    """Execute the area with Drive file data.

    Args:
        db: Database session
        area: Area to execute
        file_data: File data from Drive API
        now: Current timestamp
    """
    # Re-attach the Area instance to the current session
    area = db.merge(area)
    area_id_str = str(area.id)
    execution_log = None

    try:
        # Create execution log entry
        execution_log_start = ExecutionLogCreate(
            area_id=area.id,
            status="Started",
            output=None,
            error_message=None,
            step_details={
                "event": {
                    "now": now.isoformat(),
                    "area_id": area_id_str,
                    "user_id": str(area.user_id),
                    "file_id": file_data.get('id'),
                    "file_name": file_data.get('name'),
                }
            }
        )
        execution_log = create_execution_log(db, execution_log_start)

        # Use extract_google_drive_variables to get variables from file
        variables = extract_google_drive_variables(file_data)

        # Build trigger_data with drive variables
        trigger_data = {
            **variables,  # Include all extracted drive.* variables
            "now": now.isoformat(),
            "timestamp": now.timestamp(),
            "area_id": area_id_str,
            "user_id": str(area.user_id),
        }

        # Execute area
        result = execute_area(db, area, trigger_data)

        # Update execution log
        execution_log.status = "Success" if result["status"] == "success" else "Failed"
        execution_log.output = f"Google Drive trigger executed: {result['steps_executed']} step(s)"
        execution_log.error_message = result.get("error")
        execution_log.step_details = {
            "execution_log": result.get("execution_log", []),
            "steps_executed": result["steps_executed"],
            "file_id": file_data.get('id'),
        }
        db.commit()

        logger.info(
            "Google Drive trigger executed",
            extra={
                "area_id": area_id_str,
                "area_name": area.name,
                "user_id": str(area.user_id),
                "file_id": file_data.get('id'),
                "file_name": file_data.get('name'),
                "mime_type": file_data.get('mimeType'),
                "status": result["status"],
                "steps_executed": result.get("steps_executed", 0),
            },
        )

    except Exception as e:
        # Update execution log with failure
        if execution_log:
            execution_log.status = "Failed"
            execution_log.error_message = str(e)
            db.commit()

        logger.error(
            "Error executing Google Drive trigger",
            extra={
                "area_id": area_id_str,
                "error": str(e),
            },
            exc_info=True,
        )


def start_google_drive_scheduler() -> None:
    """Start the Google Drive polling scheduler task."""
    global _google_drive_scheduler_task

    if _google_drive_scheduler_task is not None:
        logger.warning("Google Drive scheduler task already running")
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.error("No event loop running, cannot start Google Drive scheduler")
        return

    _google_drive_scheduler_task = loop.create_task(google_drive_scheduler_task())
    logger.info("Google Drive scheduler task started")


def stop_google_drive_scheduler() -> None:
    """Stop the Google Drive polling scheduler task."""
    global _google_drive_scheduler_task

    if _google_drive_scheduler_task is not None:
        _google_drive_scheduler_task.cancel()
        _google_drive_scheduler_task = None
        logger.info("Google Drive scheduler task stopped")


def is_google_drive_scheduler_running() -> bool:
    """Check if the Google Drive scheduler task is running.

    Returns:
        True if scheduler is running and not done/cancelled, False otherwise
    """
    global _google_drive_scheduler_task
    return _google_drive_scheduler_task is not None and not _google_drive_scheduler_task.done()


def clear_google_drive_seen_state() -> None:
    """Clear the in-memory seen files state (useful for testing)."""
    global _last_seen_files, _last_page_tokens
    _last_seen_files.clear()
    _last_page_tokens.clear()


__all__ = [
    "google_drive_scheduler_task",
    "start_google_drive_scheduler",
    "is_google_drive_scheduler_running",
    "stop_google_drive_scheduler",
    "clear_google_drive_seen_state",
]
