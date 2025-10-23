"""Service for managing OAuth-based service connections."""

from __future__ import annotations

import secrets
from typing import Optional
from sqlalchemy.orm import Session

from app.integrations.oauth.factory import OAuth2ProviderFactory
from app.integrations.oauth.exceptions import OAuth2Error
from app.models.service_connection import ServiceConnection
from app.services.service_connections import (
    create_service_connection,
    get_service_connection_by_user_and_service,
    ServiceConnectionCreate,
    DuplicateServiceConnectionError,
)


class OAuthConnectionService:
    """Service for managing OAuth-based service connections."""

    @staticmethod
    def generate_oauth_state() -> str:
        """Generate secure state parameter for OAuth flow."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def get_authorization_url(provider_name: str, state: str) -> str:
        """Get authorization URL for provider."""
        provider = OAuth2ProviderFactory.create_provider(provider_name)
        return provider.get_authorization_url(state)

    @staticmethod
    async def handle_oauth_callback(
        provider_name: str,
        code: str,
        user_id: str,
        db: Session,
    ) -> ServiceConnection:
        """Handle OAuth callback and create service connection."""

        # Check if connection already exists
        existing_connection = get_service_connection_by_user_and_service(
            db, user_id, provider_name
        )
        if existing_connection:
            raise DuplicateServiceConnectionError(user_id, provider_name)

        try:
            # Exchange code for tokens
            provider = OAuth2ProviderFactory.create_provider(provider_name)
            token_set = await provider.exchange_code_for_tokens(code)

            # Get user info for verification
            user_info = await provider.get_user_info(token_set.access_token)

            # Create service connection with metadata in single transaction
            connection_data = ServiceConnectionCreate(
                service_name=provider_name,
                access_token=token_set.access_token,
                refresh_token=token_set.refresh_token,
                expires_at=None,  # GitHub tokens don't expire
            )

            oauth_metadata = {
                "provider": provider_name,
                "user_info": {
                    "id": user_info.get("id"),
                    "login": user_info.get("login"),
                    "name": user_info.get("name"),
                    "email": user_info.get("email"),
                },
                "scopes": token_set.scope.split(",") if token_set.scope else [],
                "token_type": token_set.token_type,
            }

            connection = create_service_connection(
                db, connection_data, user_id, oauth_metadata
            )
            return connection

        except Exception as e:
            db.rollback()
            raise OAuth2Error(f"Failed to create OAuth connection: {str(e)}")

    @staticmethod
    async def validate_connection(connection: ServiceConnection) -> bool:
        """Validate that a service connection is still active."""
        try:
            if not connection.oauth_metadata:
                return False

            provider_name = connection.oauth_metadata.get("provider")
            if not provider_name:
                return False

            provider = OAuth2ProviderFactory.create_provider(provider_name)

            # Decrypt the access token (assuming it's encrypted)
            from app.core.encryption import decrypt_token

            access_token = decrypt_token(connection.encrypted_access_token)
            return await provider.validate_token(access_token)

        except Exception:
            return False

    @staticmethod
    async def get_connection_user_info(connection: ServiceConnection) -> Optional[dict]:
        """Get user info from the provider using the stored token."""
        try:
            if not connection.oauth_metadata:
                return None

            provider_name = connection.oauth_metadata.get("provider")
            if not provider_name:
                return None

            provider = OAuth2ProviderFactory.create_provider(provider_name)

            # Decrypt the access token
            from app.core.encryption import decrypt_token

            access_token = decrypt_token(connection.encrypted_access_token)
            return await provider.get_user_info(access_token)

        except Exception:
            return None


__all__ = ["OAuthConnectionService"]
