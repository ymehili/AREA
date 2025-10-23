"""Gmail plugin for AREA - Implements email automation actions and reactions."""

from __future__ import annotations

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

from app.db.session import SessionLocal
from app.services.service_connections import (
    get_service_connection_by_user_and_service,
    update_service_connection,
)
from app.schemas.service_connection import ServiceConnectionUpdate
from app.core.config import settings
from app.integrations.simple_plugins.exceptions import (
    GmailAuthError,
    GmailAPIError,
    GmailConnectionError,
)

if TYPE_CHECKING:
    from app.models.area import Area

logger = logging.getLogger("area")


def _get_gmail_service(area: Area, db=None):
    """Get authenticated Gmail API service for a user.

    Args:
        area: The Area containing user_id
        db: Database session (optional, will create if not provided)

    Returns:
        Gmail API service object

    Raises:
        Exception: If service connection not found or authentication fails
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # Get service connection for Gmail
        connection = get_service_connection_by_user_and_service(
            db, area.user_id, "gmail"
        )
        if not connection:
            raise GmailConnectionError(
                "Gmail service connection not found. Please connect your Gmail account."
            )

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
                    "Failed to refresh Gmail token",
                    extra={
                        "user_id": str(area.user_id),
                        "area_id": str(area.id),
                        "error": str(refresh_err),
                    },
                    exc_info=True,
                )
                # Preserve the expected error message for tests and callers
                raise GmailAuthError("Failed to refresh Gmail token") from refresh_err

        # Build Gmail service
        service = build("gmail", "v1", credentials=creds)
        return service
    finally:
        if close_db:
            db.close()


def send_email_handler(area: Area, params: dict, event: dict) -> None:
    """Send an email via Gmail API.

    Args:
        area: The Area being executed
        params: Action parameters with 'to', 'subject', 'body', optional 'cc', 'bcc'
        event: Event data from trigger
    """
    try:
        # Extract parameters
        to_email = params.get("to")
        subject = params.get("subject", "")
        body = params.get("body", "")
        cc = params.get("cc")
        bcc = params.get("bcc")

        logger.info(
            "Starting Gmail send_email action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "to_email": to_email,
                "subject": subject,
                "body_length": len(body) if body else 0,
                "cc": cc,
                "bcc": bcc,
                "params": params,
            },
        )

        if not to_email:
            raise ValueError("'to' parameter is required for send_email action")

        # Get Gmail service
        service = _get_gmail_service(area)

        # Create MIME message
        message = MIMEMultipart()
        message["To"] = to_email
        message["Subject"] = subject

        if cc:
            message["Cc"] = cc
        if bcc:
            message["Bcc"] = bcc

        # Add body
        message.attach(MIMEText(body, "plain"))

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        # Send via Gmail API
        result = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw_message})
            .execute()
        )

        logger.info(
            "Email sent successfully",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "to": to_email,
                "subject": subject,
                "message_id": result.get("id"),
                "thread_id": result.get("threadId"),
                "cc": cc,
                "bcc": bcc,
                "body_length": len(body) if body else 0,
            },
        )
    except HttpError as e:
        logger.error(
            "Gmail API error sending email",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise GmailAPIError(f"Failed to send email: {e}") from e
    except Exception as e:
        logger.error(
            "Error sending email",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise


def mark_as_read_handler(area: Area, params: dict, event: dict) -> None:
    """Mark an email as read by removing the UNREAD label.

    Args:
        area: The Area being executed
        params: Action parameters with 'message_id'
        event: Event data from trigger (may contain message_id)
    """
    try:
        # Get message ID from params or event
        message_id = params.get("message_id")
        if not message_id:
            # Try to get from event (trigger data)
            message_id = event.get("gmail.message_id") or event.get("message_id")

        logger.info(
            "Starting Gmail mark_as_read action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "message_id": message_id,
                "params": params,
                "event_keys": list(event.keys()) if event else [],
            },
        )

        if not message_id:
            raise ValueError(
                "'message_id' is required to mark email as read. Use {{gmail.message_id}} from trigger."
            )

        # Get Gmail service
        service = _get_gmail_service(area)

        # Remove UNREAD label
        result = (
            service.users()
            .messages()
            .modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]})
            .execute()
        )

        logger.info(
            "Email marked as read successfully",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "message_id": message_id,
                "thread_id": result.get("threadId"),
                "label_ids": result.get("labelIds", []),
            },
        )
    except HttpError as e:
        logger.error(
            "Gmail API error marking email as read",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise GmailAPIError(f"Failed to mark email as read: {e}") from e
    except Exception as e:
        logger.error(
            "Error marking email as read",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise


def forward_email_handler(area: Area, params: dict, event: dict) -> None:
    """Forward an email to another recipient.

    Args:
        area: The Area being executed
        params: Action parameters with 'message_id', 'to', optional 'comment'
        event: Event data from trigger
    """
    try:
        # Get parameters
        message_id = params.get("message_id")
        if not message_id:
            # Try to get from event
            message_id = event.get("gmail.message_id") or event.get("message_id")

        to_email = params.get("to")
        comment = params.get("comment", "")

        logger.info(
            "Starting Gmail forward_email action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "message_id": message_id,
                "to_email": to_email,
                "comment_length": len(comment) if comment else 0,
                "params": params,
                "event_keys": list(event.keys()) if event else [],
            },
        )

        if not message_id:
            raise ValueError(
                "'message_id' is required to forward email. Use {{gmail.message_id}} from trigger."
            )
        if not to_email:
            raise ValueError("'to' parameter is required for forward_email action")

        # Get Gmail service
        service = _get_gmail_service(area)

        # Fetch original message
        original_message = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

        # Extract original subject and body
        headers = original_message["payload"].get("headers", [])
        original_subject = ""
        original_from = ""
        for header in headers:
            if header["name"].lower() == "subject":
                original_subject = header["value"]
            elif header["name"].lower() == "from":
                original_from = header["value"]

        # Get original body (simplified - only gets plain text)
        original_body = ""
        if "parts" in original_message["payload"]:
            for part in original_message["payload"]["parts"]:
                if part["mimeType"] == "text/plain":
                    body_data = part["body"].get("data", "")
                    if body_data:
                        original_body = base64.urlsafe_b64decode(body_data).decode(
                            "utf-8"
                        )
                        break
        elif "body" in original_message["payload"]:
            body_data = original_message["payload"]["body"].get("data", "")
            if body_data:
                original_body = base64.urlsafe_b64decode(body_data).decode("utf-8")

        # Create forwarded message
        message = MIMEMultipart()
        message["To"] = to_email
        message["Subject"] = f"Fwd: {original_subject}"

        # Build forwarded body
        forwarded_body = ""
        if comment:
            forwarded_body += f"{comment}\n\n"

        forwarded_body += "---------- Forwarded message ----------\n"
        forwarded_body += f"From: {original_from}\n"
        forwarded_body += f"Subject: {original_subject}\n\n"
        forwarded_body += original_body

        message.attach(MIMEText(forwarded_body, "plain"))

        # Encode and send
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        result = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw_message})
            .execute()
        )

        logger.info(
            "Email forwarded successfully",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "original_message_id": message_id,
                "original_thread_id": original_message.get("threadId"),
                "to": to_email,
                "forwarded_message_id": result.get("id"),
                "forwarded_thread_id": result.get("threadId"),
                "comment_length": len(comment) if comment else 0,
                "original_subject": original_subject,
                "original_from": original_from,
            },
        )
    except HttpError as e:
        logger.error(
            "Gmail API error forwarding email",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise GmailAPIError(f"Failed to forward email: {e}") from e
    except Exception as e:
        logger.error(
            "Error forwarding email",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise


__all__ = [
    "send_email_handler",
    "mark_as_read_handler",
    "forward_email_handler",
]
