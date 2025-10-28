"""Shared utilities for Outlook integration."""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING

import httpx

from app.core.config import settings
from app.core.encryption import decrypt_token
from app.services.service_connections import update_service_connection
from app.schemas.service_connection import ServiceConnectionUpdate

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.models.service_connection import ServiceConnection

logger = logging.getLogger("area")


async def refresh_outlook_token(
    connection: "ServiceConnection",
    db: "Session",
    user_id: str | None = None,
    area_id: str | None = None,
) -> str:
    """Refresh an expired Outlook OAuth token.

    Args:
        connection: ServiceConnection object with encrypted tokens
        db: Database session for persisting updated tokens
        user_id: Optional user ID for logging context
        area_id: Optional area ID for logging context

    Returns:
        The new access token

    Raises:
        Exception: If token refresh fails
    """
    # Decrypt refresh token
    refresh_token = None
    if connection.encrypted_refresh_token:
        refresh_token = decrypt_token(connection.encrypted_refresh_token)

    if not refresh_token:
        raise ValueError("No refresh token available")

    log_extra = {}
    if user_id:
        log_extra["user_id"] = str(user_id)
    if area_id:
        log_extra["area_id"] = str(area_id)

    logger.info("Refreshing expired Outlook token", extra=log_extra)

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

        # Update tokens
        now = datetime.now(timezone.utc)
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
            extra={**log_extra, "new_expires_at": new_expires_at.isoformat()},
        )

        return access_token


def is_token_expired(connection: "ServiceConnection") -> bool:
    """Check if an Outlook connection's token is expired.

    Args:
        connection: ServiceConnection object

    Returns:
        True if token is expired (with 5 minute buffer), False otherwise
    """
    if not connection.expires_at:
        return False

    now = datetime.now(timezone.utc)
    # Add 5 minute buffer for clock skew
    return connection.expires_at <= now + timedelta(minutes=5)


async def get_outlook_access_token(
    connection: "ServiceConnection",
    db: "Session",
    user_id: str | None = None,
    area_id: str | None = None,
) -> str:
    """Get a valid Outlook access token, refreshing if necessary.

    Args:
        connection: ServiceConnection object with encrypted tokens
        db: Database session for persisting updated tokens
        user_id: Optional user ID for logging context
        area_id: Optional area ID for logging context

    Returns:
        A valid access token

    Raises:
        Exception: If token refresh fails
    """
    # Check if token is expired first
    if is_token_expired(connection):
        # We need to refresh the token
        if not connection.encrypted_refresh_token:
            raise Exception("No refresh token available to refresh expired access token")
        
        refresh_token = decrypt_token(connection.encrypted_refresh_token)
        if not refresh_token:
            raise Exception("Could not decrypt refresh token")
        
        access_token = await refresh_outlook_token(connection, db, user_id, area_id)
        return access_token
    else:
        # Token is not expired, just return the current access token
        access_token = decrypt_token(connection.encrypted_access_token)
        if not access_token:
            # If we can't decrypt the access token but the refresh token exists, try to refresh
            if connection.encrypted_refresh_token:
                refresh_token = decrypt_token(connection.encrypted_refresh_token)
                if refresh_token:
                    access_token = await refresh_outlook_token(connection, db, user_id, area_id)
                    return access_token
            raise Exception("Could not decrypt access token and no valid refresh token available")
        
        return access_token
