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
    
    @patch('app.integrations.oauth.OAuth')
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
    
    @patch('app.integrations.oauth.OAuth')
    @pytest.mark.asyncio
    async def test_get_google_authorization_url(self, mock_oauth_class):
        """Test getting Google authorization URL."""
        # Setup mocks
        mock_oauth_instance = Mock()
        mock_google = Mock()
        mock_oauth_instance.google = mock_google
        mock_oauth_class.return_value = mock_oauth_instance
        
        # Mock the authorize_redirect method
        expected_redirect = RedirectResponse(url="https://accounts.google.com/oauth/authorize?...")
        mock_google.authorize_redirect = AsyncMock(return_value=expected_redirect)
        
        mock_request = Mock()
        
        # Test the method
        result = await OAuthService.get_google_authorization_url(mock_request)
        
        # Verify the result
        assert result == expected_redirect
        mock_google.authorize_redirect.assert_called_once_with(
            mock_request, 
            "http://localhost:8080/api/v1/oauth/google/callback"
        )
    
    @patch('app.integrations.oauth.OAuth')
    @patch('app.integrations.oauth.OAuthService._find_or_create_google_user')
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
        mock_user.id = 1
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
    
    @patch('app.integrations.oauth.OAuth')
    @patch('app.integrations.oauth.OAuthService._find_or_create_google_user')
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
        mock_user.id = 1
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
    
    @patch('app.integrations.oauth.OAuth')
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

    @patch('app.integrations.oauth.get_user_by_email')
    @patch('app.integrations.oauth.create_user')
    def test_find_or_create_google_user_new_user(self, mock_create_user, mock_get_user_by_email):
        """Test creating a new Google user."""
        # Setup mocks
        mock_db = Mock()
        mock_get_user_by_email.return_value = None  # No existing user
        
        # Mock the database query for Google sub
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None  # No user with this Google sub
        mock_db.query.return_value = mock_query
        
        # Mock user creation
        mock_user = Mock()
        mock_user.id = 1
        mock_create_user.return_value = mock_user
        
        # Test the method
        result = OAuthService._find_or_create_google_user(
            mock_db, 
            'newuser@example.com', 
            'google123456'
        )
        
        # Verify user creation was called
        mock_create_user.assert_called_once()
        assert result == mock_user
    
    @patch('app.integrations.oauth.get_user_by_email')
    def test_find_or_create_google_user_existing_user_by_google_sub(self, mock_get_user_by_email):
        """Test finding existing user by Google sub."""
        # Setup mocks
        mock_db = Mock()
        
        # Mock existing user found by Google sub
        mock_user = Mock()
        mock_user.id = 1
        mock_user.google_oauth_sub = 'google123456'
        
        # Mock the database query for Google sub to return existing user
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
    
    def test_generate_redirect_url_web(self):
        """Test redirect URL generation for web clients."""
        result = OAuthService.generate_redirect_url("test_token", "Mozilla/5.0")
        assert result == "http://localhost:3000#access_token=test_token"
    
    def test_generate_redirect_url_mobile(self):
        """Test redirect URL generation for mobile clients."""
        result = OAuthService.generate_redirect_url("test_token", "Mobile Safari")
        assert result == "http://localhost:3000/oauth/callback?access_token=test_token"
    
    def test_is_oauth_configured(self):
        """Test OAuth configuration check."""
        # This would test the configuration validation
        # The actual result depends on your test environment settings
        result = OAuthService.is_oauth_configured()
        assert isinstance(result, bool)