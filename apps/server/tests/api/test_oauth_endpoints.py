"""Tests covering OAuth authentication API endpoints."""

from __future__ import annotations

import uuid
from unittest.mock import patch, Mock, AsyncMock, MagicMock
import pytest
from starlette.responses import RedirectResponse

from app.services import get_user_by_email
from app.integrations.oauth import OAuthService
from app.schemas.auth import TokenResponse
from tests.conftest import SyncASGITestClient


class TestOAuthEndpoints:
    """Test OAuth API endpoints."""
    
    def setup_method(self):
        """Reset OAuth client before each test."""
        OAuthService._reset_oauth_client()
    
    @patch('app.integrations.oauth.OAuthService.get_google_authorization_url')
    def test_oauth_google_initiate_redirects_to_google(self, mock_get_url, client: SyncASGITestClient) -> None:
        """Test that OAuth initiation delegates to service layer."""
        # Mock the service method to return a proper RedirectResponse
        # This avoids the recursion issue with Mock objects
        mock_redirect = RedirectResponse(url="https://accounts.google.com/oauth/authorize?...")
        mock_get_url.return_value = mock_redirect
        
        response = client.get("/api/v1/oauth/google")
        
        # Verify the service method was called
        mock_get_url.assert_called_once()
        # Should get a redirect response
        assert response.status_code == 307
    
    @patch('app.integrations.oauth.OAuthService.handle_google_callback')
    @patch('app.integrations.oauth.OAuthService.generate_redirect_url')
    def test_oauth_google_callback_creates_user(
        self, 
        mock_generate_redirect, 
        mock_handle_callback, 
        client: SyncASGITestClient, 
        db_session
    ) -> None:
        """Test that OAuth callback creates a new user via service layer."""
        # Mock the service layer responses
        mock_token_response = TokenResponse(access_token="mock_token")
        mock_handle_callback.return_value = mock_token_response
        mock_generate_redirect.return_value = "http://localhost:3000#access_token=mock_token"
        
        response = client.get("/api/v1/oauth/google/callback")
        
        # Should redirect (307) to frontend with token
        assert response.status_code == 307
        mock_handle_callback.assert_called_once()
        mock_generate_redirect.assert_called_once()
    
    def test_oauth_unsupported_provider_returns_400(self, client: SyncASGITestClient) -> None:
        """Test that unsupported OAuth providers return 400 error."""
        response = client.get("/api/v1/oauth/github")
        assert response.status_code == 400
        assert "Unsupported" in response.json()["detail"]
    
    def test_oauth_callback_unsupported_provider_returns_400(self, client: SyncASGITestClient) -> None:
        """Test that unsupported OAuth provider callbacks return 400 error."""
        response = client.get("/api/v1/oauth/github/callback")
        assert response.status_code == 400
        assert "Unsupported" in response.json()["detail"]


class TestOAuthService:
    """Test OAuth service layer directly."""
    
    def setup_method(self):
        """Reset OAuth client before each test."""
        OAuthService._reset_oauth_client()
    
    @patch('app.integrations.user_oauth.OAuth')
    def test_oauth_client_creation(self, mock_oauth_class):
        """Test that OAuth client is created correctly."""
        mock_oauth_instance = Mock()
        mock_oauth_class.return_value = mock_oauth_instance
        
        # This should trigger OAuth client creation
        client = OAuthService._get_oauth_client()
        
        # Verify OAuth was instantiated and Google was registered
        mock_oauth_class.assert_called_once()
        mock_oauth_instance.register.assert_called_once()
        
        # Verify the register call has correct parameters
        call_args = mock_oauth_instance.register.call_args
        assert call_args[1]['name'] == 'google'  # Check kwargs
    
    @patch('app.integrations.user_oauth.OAuth')
    @patch('app.integrations.user_oauth.OAuthService._find_or_create_google_user')
    @pytest.mark.asyncio
    async def test_handle_google_callback_new_user(self, mock_find_or_create, mock_oauth_class):
        """Test handling Google callback for new user."""
        # Setup OAuth mocks
        mock_oauth_instance = Mock()
        mock_google = Mock()
        mock_oauth_instance.google = mock_google
        mock_oauth_class.return_value = mock_oauth_instance
        
        # Mock the token response
        mock_token = {
            'userinfo': {
                'email': 'newuser@example.com',
                'sub': 'google123456'
            }
        }
        mock_google.authorize_access_token = AsyncMock(return_value=mock_token)
        
        # Mock user creation by mocking the entire _find_or_create_google_user method
        mock_user = Mock()
        mock_user.id = uuid.uuid4()  # Use proper UUID for the user ID
        mock_find_or_create.return_value = mock_user
        
        mock_request = Mock()
        mock_db = Mock()  # Use a mock DB session
        
        # Test the method
        result = await OAuthService.handle_google_callback(mock_request, mock_db)
        
        # Verify result
        assert isinstance(result, TokenResponse)
        assert result.access_token is not None
        
        # Verify the user finding/creation method was called
        mock_find_or_create.assert_called_once_with(mock_db, 'newuser@example.com', 'google123456')
    
    @patch('app.integrations.user_oauth.OAuth')
    @patch('app.integrations.user_oauth.OAuthService._find_or_create_google_user')
    @pytest.mark.asyncio
    async def test_handle_google_callback_existing_user(self, mock_find_or_create, mock_oauth_class):
        """Test handling Google callback for existing user."""
        # Setup OAuth mocks
        mock_oauth_instance = Mock()
        mock_google = Mock()
        mock_oauth_instance.google = mock_google
        mock_oauth_class.return_value = mock_oauth_instance
        
        # Mock the token response
        mock_token = {
            'userinfo': {
                'email': 'existing@example.com',
                'sub': 'google123456'
            }
        }
        mock_google.authorize_access_token = AsyncMock(return_value=mock_token)
        
        # Mock existing user
        mock_user = Mock()
        mock_user.id = uuid.uuid4()  # Use proper UUID for the user ID
        mock_user.google_oauth_sub = 'google123456'
        mock_find_or_create.return_value = mock_user
        
        mock_request = Mock()
        mock_db = Mock()  # Use a mock DB session
        
        # Test the method
        result = await OAuthService.handle_google_callback(mock_request, mock_db)
        
        # Verify result
        assert isinstance(result, TokenResponse)
        assert result.access_token is not None
        
        # Verify the user finding method was called
        mock_find_or_create.assert_called_once_with(mock_db, 'existing@example.com', 'google123456')
    
    @patch('app.integrations.user_oauth.OAuth')
    @pytest.mark.asyncio
    async def test_handle_google_callback_missing_userinfo(self, mock_oauth_class):
        """Test that missing user info raises appropriate exception."""
        from fastapi import HTTPException
        
        # Setup OAuth mocks
        mock_oauth_instance = Mock()
        mock_google = Mock()
        mock_oauth_instance.google = mock_google
        mock_oauth_class.return_value = mock_oauth_instance
        
        # Mock token response without userinfo
        mock_token = {}
        mock_google.authorize_access_token = AsyncMock(return_value=mock_token)
        
        mock_request = Mock()
        mock_db = Mock()
        
        # Test that it raises HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await OAuthService.handle_google_callback(mock_request, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "user information" in exc_info.value.detail

    @patch('app.integrations.user_oauth.create_user')
    @patch('app.integrations.user_oauth.get_user_by_email')
    def test_find_or_create_google_user_new_user(self, mock_get_user_by_email, mock_create_user):
        """Test creating a new Google user."""
        # Setup mocks
        mock_db = Mock()
        mock_get_user_by_email.return_value = None  # No existing user by email

        # Mock the database query for Google sub
        from app.models.user import User
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None  # No user with this Google sub
        mock_db.query.return_value = mock_query

        # Mock the created user
        mock_user = Mock()
        mock_user.id = uuid.uuid4()  # Use proper UUID for the user ID
        mock_user.email = 'newuser@example.com'
        mock_user.google_oauth_sub = 'google123456'
        mock_user.is_confirmed = True
        mock_user.hashed_password = ""
        mock_create_user.return_value = mock_user

        # Test the method
        result = OAuthService._find_or_create_google_user(
            mock_db,
            'newuser@example.com',  # Fixed: removed space that made it invalid
            'google123456'
        )

        # Verify user was created by checking create_user was called
        mock_create_user.assert_called_once()
        
        # Verify OAuth-specific fields were set
        assert mock_user.hashed_password == ""
        assert mock_user.google_oauth_sub == 'google123456'
        assert mock_user.is_confirmed is True
        
        # Verify db.add was called for both the user object and the activity log
        assert mock_db.add.call_count == 2
        # Verify that the user was added to the session
        calls = mock_db.add.call_args_list
        # At least one of the calls should be for the user object
        user_added = any(call[0][0] == mock_user for call in calls)
        assert user_added, "User object should have been added to the session"
        mock_db.commit.assert_called()
        mock_db.refresh.assert_called()
        # Verify the result has the expected attributes
        assert result.email == 'newuser@example.com'
        assert result.google_oauth_sub == 'google123456'
        assert result.is_confirmed is True
        assert result.hashed_password == ""
    
    @patch('app.integrations.user_oauth.get_user_by_email')
    def test_find_or_create_google_user_existing_user_by_google_sub(self, mock_get_user_by_email):
        """Test finding existing user by Google sub."""
        # Setup mocks
        mock_db = Mock()
        
        # Mock existing user found by Google sub
        mock_user = Mock()
        mock_user.id = uuid.uuid4()  # Use proper UUID for the user ID
        mock_user.google_oauth_sub = 'google123456'
        
        # Mock the database query for Google sub to return existing user
        from app.models.user import User
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_user
        mock_db.query.return_value = mock_query
        
        # Test the method
        result = OAuthService._find_or_create_google_user(
            mock_db, 
            'existing@example.com', 
            'google123456'
        )
        
        # Should return the existing user, no creation should happen
        assert result == mock_user
        mock_get_user_by_email.assert_not_called()
    
    def test_is_oauth_configured(self):
        """Test OAuth configuration check."""
        # This would test the configuration validation
        # The actual result depends on your test environment settings
        result = OAuthService.is_oauth_configured()
        assert isinstance(result, bool)