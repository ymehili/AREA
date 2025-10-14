"""Outlook plugin for AREA - Implements email automation actions and reactions via Microsoft Graph API."""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING, Any, Dict
from datetime import datetime, timezone, timedelta

import httpx

from app.db.session import SessionLocal
from app.services.service_connections import (
    get_service_connection_by_user_and_service,
    update_service_connection,
)
from app.schemas.service_connection import ServiceConnectionUpdate
from app.core.config import settings
from app.core.encryption import decrypt_token
from app.integrations.simple_plugins.exceptions import (
    GmailAuthError,
    GmailAPIError,
    GmailConnectionError,
)

if TYPE_CHECKING:
    from app.models.area import Area

logger = logging.getLogger("area")


# Exception classes specific to Outlook
class OutlookConnectionError(GmailConnectionError):
    """Raised when Outlook service connection is not found."""
    pass


class OutlookAuthError(GmailAuthError):
    """Raised when Outlook authentication fails."""
    pass


class OutlookAPIError(GmailAPIError):
    """Raised when Outlook/Microsoft Graph API call fails."""
    pass


async def _get_outlook_client(area: Area, db=None) -> httpx.AsyncClient:
    """Get authenticated httpx client for Microsoft Graph API.

    Args:
        area: The Area containing user_id
        db: Database session (optional, will create if not provided)

    Returns:
        Authenticated httpx.AsyncClient configured for Microsoft Graph API

    Raises:
        OutlookConnectionError: If service connection not found
        OutlookAuthError: If authentication fails or token refresh fails
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # Get service connection for Outlook
        connection = get_service_connection_by_user_and_service(db, area.user_id, "outlook")
        if not connection:
            raise OutlookConnectionError(
                "Outlook service connection not found. Please connect your Outlook account."
            )

        # Decrypt tokens
        access_token = decrypt_token(connection.encrypted_access_token)
        refresh_token = None
        if connection.encrypted_refresh_token:
            refresh_token = decrypt_token(connection.encrypted_refresh_token)

        # Check if token is expired
        now = datetime.now(timezone.utc)
        token_expired = False
        if connection.expires_at:
            # Add 5 minute buffer for clock skew
            token_expired = connection.expires_at <= now + timedelta(minutes=5)

        # Refresh token if expired
        if token_expired and refresh_token:
            try:
                logger.info(
                    "Refreshing expired Outlook token",
                    extra={
                        "user_id": str(area.user_id),
                        "area_id": str(area.id),
                    },
                )

                # Use Microsoft token endpoint to refresh
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded",
                        },
                        data={
                            "client_id": settings.microsoft_client_id,
                            "client_secret": settings.microsoft_client_secret,
                            "refresh_token": refresh_token,
                            "grant_type": "refresh_token",
                        },
                    )
                    response.raise_for_status()
                    token_data = response.json()

                    # Update access token
                    access_token = token_data["access_token"]
                    new_refresh_token = token_data.get("refresh_token", refresh_token)
                    expires_in = token_data.get("expires_in", 3600)
                    new_expires_at = now + timedelta(seconds=expires_in)

                    # Persist updated tokens
                    update_service_connection(
                        db,
                        str(connection.id),
                        ServiceConnectionUpdate(
                            service_name=connection.service_name,
                            access_token=access_token,
                            refresh_token=new_refresh_token,
                            expires_at=new_expires_at,
                        ),
                    )

                    logger.info(
                        "Outlook token refreshed successfully",
                        extra={
                            "user_id": str(area.user_id),
                            "area_id": str(area.id),
                        },
                    )

            except Exception as refresh_err:
                logger.error(
                    "Failed to refresh Outlook token",
                    extra={
                        "user_id": str(area.user_id),
                        "area_id": str(area.id),
                        "error": str(refresh_err),
                    },
                    exc_info=True,
                )
                raise OutlookAuthError("Failed to refresh Outlook token") from refresh_err

        # Create authenticated client
        client = httpx.AsyncClient(
            base_url="https://graph.microsoft.com/v1.0",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

        return client
    finally:
        if close_db:
            db.close()


async def send_email_handler(area: Area, params: dict, event: dict) -> None:
    """Send an email via Microsoft Graph API.

    Args:
        area: The Area being executed
        params: Action parameters with 'to', 'subject', 'body', optional 'cc', 'bcc'
        event: Event data from trigger
    """
    client = None
    try:
        # Extract parameters
        to_email = params.get("to")
        subject = params.get("subject", "")
        body = params.get("body", "")
        cc = params.get("cc")
        bcc = params.get("bcc")

        logger.info(
            "Starting Outlook send_email action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "to_email": to_email,
                "subject": subject,
                "body_length": len(body) if body else 0,
                "cc": cc,
                "bcc": bcc,
            },
        )

        if not to_email:
            raise ValueError("'to' parameter is required for send_email action")

        # Get authenticated client
        client = await _get_outlook_client(area)

        # Build message payload for Microsoft Graph API
        message_payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": body,
                },
                "toRecipients": [{"emailAddress": {"address": to_email}}],
            }
        }

        # Add CC recipients if provided
        if cc:
            cc_list = [addr.strip() for addr in cc.split(",")]
            message_payload["message"]["ccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in cc_list
            ]

        # Add BCC recipients if provided
        if bcc:
            bcc_list = [addr.strip() for addr in bcc.split(",")]
            message_payload["message"]["bccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in bcc_list
            ]

        # Send email using Microsoft Graph API
        response = await client.post("/me/sendMail", json=message_payload)
        response.raise_for_status()

        logger.info(
            "Email sent successfully via Outlook",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "to": to_email,
                "subject": subject,
                "cc": cc,
                "bcc": bcc,
                "body_length": len(body) if body else 0,
            },
        )
    except httpx.HTTPStatusError as e:
        logger.error(
            "Outlook API error sending email",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
                "status_code": e.response.status_code if e.response else None,
            },
            exc_info=True,
        )
        raise OutlookAPIError(f"Failed to send email: {e}") from e
    except Exception as e:
        logger.error(
            "Error sending email via Outlook",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise
    finally:
        if client:
            await client.aclose()


async def mark_as_read_handler(area: Area, params: dict, event: dict) -> None:
    """Mark an email as read in Outlook by updating isRead property.

    Args:
        area: The Area being executed
        params: Action parameters with 'message_id'
        event: Event data from trigger (may contain message_id)
    """
    client = None
    try:
        # Get message ID from params or event
        message_id = params.get("message_id")
        if not message_id:
            # Try to get from event (trigger data)
            message_id = event.get("outlook.message_id") or event.get("message_id")

        logger.info(
            "Starting Outlook mark_as_read action",
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
                "'message_id' is required to mark email as read. "
                "Use {{outlook.message_id}} from trigger."
            )

        # Get authenticated client
        client = await _get_outlook_client(area)

        # Update message to mark as read
        update_payload = {"isRead": True}
        response = await client.patch(f"/me/messages/{message_id}", json=update_payload)
        response.raise_for_status()

        logger.info(
            "Email marked as read successfully in Outlook",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "message_id": message_id,
            },
        )
    except httpx.HTTPStatusError as e:
        logger.error(
            "Outlook API error marking email as read",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
                "status_code": e.response.status_code if e.response else None,
            },
            exc_info=True,
        )
        raise OutlookAPIError(f"Failed to mark email as read: {e}") from e
    except Exception as e:
        logger.error(
            "Error marking email as read in Outlook",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise
    finally:
        if client:
            await client.aclose()


async def forward_email_handler(area: Area, params: dict, event: dict) -> None:
    """Forward an email to another recipient via Outlook.

    Args:
        area: The Area being executed
        params: Action parameters with 'message_id', 'to', optional 'comment'
        event: Event data from trigger
    """
    client = None
    try:
        # Get parameters
        message_id = params.get("message_id")
        if not message_id:
            # Try to get from event
            message_id = event.get("outlook.message_id") or event.get("message_id")

        to_email = params.get("to")
        comment = params.get("comment", "")

        logger.info(
            "Starting Outlook forward_email action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "message_id": message_id,
                "to_email": to_email,
                "comment_length": len(comment) if comment else 0,
            },
        )

        if not message_id:
            raise ValueError(
                "'message_id' is required to forward email. "
                "Use {{outlook.message_id}} from trigger."
            )
        if not to_email:
            raise ValueError("'to' parameter is required for forward_email action")

        # Get authenticated client
        client = await _get_outlook_client(area)

        # Build forward payload
        forward_payload = {
            "toRecipients": [{"emailAddress": {"address": to_email}}],
        }

        # Add comment if provided
        if comment:
            forward_payload["comment"] = comment

        # Forward email using Microsoft Graph API
        response = await client.post(
            f"/me/messages/{message_id}/forward", json=forward_payload
        )
        response.raise_for_status()

        logger.info(
            "Email forwarded successfully via Outlook",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "original_message_id": message_id,
                "to": to_email,
                "comment_length": len(comment) if comment else 0,
            },
        )
    except httpx.HTTPStatusError as e:
        logger.error(
            "Outlook API error forwarding email",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
                "status_code": e.response.status_code if e.response else None,
            },
            exc_info=True,
        )
        raise OutlookAPIError(f"Failed to forward email: {e}") from e
    except Exception as e:
        logger.error(
            "Error forwarding email via Outlook",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise
    finally:
        if client:
            await client.aclose()


__all__ = [
    "send_email_handler",
    "mark_as_read_handler",
    "forward_email_handler",
    "OutlookConnectionError",
    "OutlookAuthError",
    "OutlookAPIError",
]
