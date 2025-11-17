"""Advanced tests for user OAuth service."""

from __future__ import annotations

from unittest.mock import Mock, patch, MagicMock, AsyncMock
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from app.integrations.user_oauth import OAuthService
from app.models.user import User
from app.schemas.auth import TokenResponse


class TestOAuthServiceConfiguration:
    """Test OAuth service configuration and initialization."""

    def test_is_oauth_configured_returns_true_when_configured(self):
        """Test is_oauth_configured returns True when properly configured."""
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = "test_client_secret"
            
            result = OAuthService.is_oauth_configured()
            
            assert result is True

    def test_is_oauth_configured_returns_false_when_missing_client_id(self):
        """Test is_oauth_configured returns False when client ID is missing."""
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.google_client_id = None
            mock_settings.google_client_secret = "test_client_secret"
            
            result = OAuthService.is_oauth_configured()
            
            assert result is False

    def test_is_oauth_configured_returns_false_when_missing_client_secret(self):
        """Test is_oauth_configured returns False when client secret is missing."""
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = None
            
            result = OAuthService.is_oauth_configured()
            
            assert result is False

    def test_create_oauth_client_with_valid_config(self):
        """Test OAuth client creation with valid configuration."""
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = "test_client_secret"
            
            OAuthService._reset_oauth_client()
            oauth_client = OAuthService._create_oauth_client()
            
            assert oauth_client is not None

    def test_create_oauth_client_without_config(self):
        """Test OAuth client creation without configuration."""
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.google_client_id = None
            mock_settings.google_client_secret = None
            
            OAuthService._reset_oauth_client()
            oauth_client = OAuthService._create_oauth_client()
            
            # Should still create client but without Google provider
            assert oauth_client is not None

    def test_get_oauth_client_singleton_pattern(self):
        """Test that _get_oauth_client returns the same instance."""
        OAuthService._reset_oauth_client()
        
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = "test_client_secret"
            
            client1 = OAuthService._get_oauth_client()
            client2 = OAuthService._get_oauth_client()
            
            assert client1 is client2

    def test_reset_oauth_client(self):
        """Test resetting OAuth client."""
        OAuthService._reset_oauth_client()
        assert OAuthService._oauth_client is None


class TestGoogleAuthorizationURL:
    """Test Google OAuth authorization URL generation."""

    @pytest.mark.asyncio
    async def test_get_google_authorization_url_success(self):
        """Test successful Google authorization URL generation."""
        mock_request = Mock()
        
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = "test_client_secret"
            mock_settings.oauth_redirect_base_url = "http://localhost:8080/api/v1/oauth"
            
            OAuthService._reset_oauth_client()
            
            with patch.object(OAuthService, "_get_oauth_client") as mock_get_client:
                mock_oauth = Mock()
                mock_google = Mock()
                mock_google.authorize_redirect = AsyncMock(return_value=RedirectResponse(url="https://accounts.google.com/oauth"))
                mock_oauth.google = mock_google
                mock_get_client.return_value = mock_oauth
                
                result = await OAuthService.get_google_authorization_url(mock_request)
                
                assert isinstance(result, RedirectResponse)
                mock_google.authorize_redirect.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_google_authorization_url_not_configured(self):
        """Test Google authorization URL when OAuth is not configured."""
        mock_request = Mock()
        
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.google_client_id = None
            mock_settings.google_client_secret = None
            
            with pytest.raises(HTTPException) as exc_info:
                await OAuthService.get_google_authorization_url(mock_request)
            
            assert exc_info.value.status_code == 500
            assert "not properly configured" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_google_authorization_url_oauth_error(self):
        """Test Google authorization URL when OAuth raises an error."""
        mock_request = Mock()
        
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = "test_client_secret"
            mock_settings.oauth_redirect_base_url = "http://localhost:8080/api/v1/oauth"
            
            OAuthService._reset_oauth_client()
            
            with patch.object(OAuthService, "_get_oauth_client") as mock_get_client:
                mock_oauth = Mock()
                mock_google = Mock()
                mock_google.authorize_redirect = Mock(side_effect=Exception("OAuth error"))
                mock_oauth.google = mock_google
                mock_get_client.return_value = mock_oauth
                
                with pytest.raises(HTTPException) as exc_info:
                    await OAuthService.get_google_authorization_url(mock_request)
                
                assert exc_info.value.status_code == 500
                assert "Failed to initiate OAuth" in exc_info.value.detail


class TestGoogleCallback:
    """Test Google OAuth callback handling."""

    @pytest.mark.asyncio
    async def test_handle_google_callback_success_new_user(self, db_session: Session):
        """Test successful callback for new user."""
        mock_request = Mock()
        
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = "test_client_secret"
            
            OAuthService._reset_oauth_client()
            
            with patch.object(OAuthService, "_get_oauth_client") as mock_get_client:
                mock_oauth = Mock()
                mock_google = Mock()
                mock_google.authorize_access_token = AsyncMock(return_value={
                    "userinfo": {
                        "email": "newuser@example.com",
                        "sub": "google_sub_123"
                    }
                })
                mock_oauth.google = mock_google
                mock_get_client.return_value = mock_oauth
                
                with patch("app.integrations.user_oauth.create_access_token") as mock_create_token:
                    mock_create_token.return_value = "test_access_token"
                    
                    result = await OAuthService.handle_google_callback(mock_request, db_session)
                    
                    assert isinstance(result, TokenResponse)
                    assert result.access_token == "test_access_token"
                    
                    # Verify user was created
                    user = db_session.query(User).filter(User.email == "newuser@example.com").first()
                    assert user is not None
                    assert user.google_oauth_sub == "google_sub_123"
                    assert user.is_confirmed is True

    @pytest.mark.asyncio
    async def test_handle_google_callback_success_existing_user(self, db_session: Session):
        """Test successful callback for existing user."""
        # Create existing user
        existing_user = User(
            email="existing@example.com",
            hashed_password="test",
            google_oauth_sub="google_sub_456",
            is_confirmed=True
        )
        db_session.add(existing_user)
        db_session.commit()
        
        mock_request = Mock()
        
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = "test_client_secret"
            
            OAuthService._reset_oauth_client()
            
            with patch.object(OAuthService, "_get_oauth_client") as mock_get_client:
                mock_oauth = Mock()
                mock_google = Mock()
                mock_google.authorize_access_token = AsyncMock(return_value={
                    "userinfo": {
                        "email": "existing@example.com",
                        "sub": "google_sub_456"
                    }
                })
                mock_oauth.google = mock_google
                mock_get_client.return_value = mock_oauth
                
                with patch("app.integrations.user_oauth.create_access_token") as mock_create_token:
                    mock_create_token.return_value = "test_access_token"
                    
                    result = await OAuthService.handle_google_callback(mock_request, db_session)
                    
                    assert isinstance(result, TokenResponse)
                    assert result.access_token == "test_access_token"

    @pytest.mark.asyncio
    async def test_handle_google_callback_not_configured(self, db_session: Session):
        """Test callback when OAuth is not configured."""
        mock_request = Mock()
        
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.google_client_id = None
            mock_settings.google_client_secret = None
            
            with pytest.raises(HTTPException) as exc_info:
                await OAuthService.handle_google_callback(mock_request, db_session)
            
            assert exc_info.value.status_code == 500
            assert "not properly configured" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_handle_google_callback_missing_userinfo(self, db_session: Session):
        """Test callback when userinfo is missing."""
        mock_request = Mock()
        
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = "test_client_secret"
            
            OAuthService._reset_oauth_client()
            
            with patch.object(OAuthService, "_get_oauth_client") as mock_get_client:
                mock_oauth = Mock()
                mock_google = Mock()
                mock_google.authorize_access_token = AsyncMock(return_value={})
                mock_oauth.google = mock_google
                mock_get_client.return_value = mock_oauth
                
                with pytest.raises(HTTPException) as exc_info:
                    await OAuthService.handle_google_callback(mock_request, db_session)
                
                assert exc_info.value.status_code == 400
                assert "Unable to retrieve user information" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_handle_google_callback_missing_email(self, db_session: Session):
        """Test callback when email is missing."""
        mock_request = Mock()
        
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = "test_client_secret"
            
            OAuthService._reset_oauth_client()
            
            with patch.object(OAuthService, "_get_oauth_client") as mock_get_client:
                mock_oauth = Mock()
                mock_google = Mock()
                mock_google.authorize_access_token = AsyncMock(return_value={
                    "userinfo": {
                        "sub": "google_sub_123"
                    }
                })
                mock_oauth.google = mock_google
                mock_get_client.return_value = mock_oauth
                
                with pytest.raises(HTTPException) as exc_info:
                    await OAuthService.handle_google_callback(mock_request, db_session)
                
                assert exc_info.value.status_code == 400
                assert "Email or Google ID not provided" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_handle_google_callback_oauth_exception(self, db_session: Session):
        """Test callback when OAuth raises an exception."""
        mock_request = Mock()
        
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = "test_client_secret"
            
            OAuthService._reset_oauth_client()
            
            with patch.object(OAuthService, "_get_oauth_client") as mock_get_client:
                mock_oauth = Mock()
                mock_google = Mock()
                mock_google.authorize_access_token = AsyncMock(side_effect=Exception("OAuth error"))
                mock_oauth.google = mock_google
                mock_get_client.return_value = mock_oauth
                
                with pytest.raises(HTTPException) as exc_info:
                    await OAuthService.handle_google_callback(mock_request, db_session)
                
                assert exc_info.value.status_code == 400
                assert "OAuth authentication failed" in exc_info.value.detail


class TestFindOrCreateGoogleUser:
    """Test finding or creating Google users."""

    def test_find_or_create_existing_user_by_google_sub(self, db_session: Session):
        """Test finding existing user by Google sub."""
        # Create existing user
        existing_user = User(
            email="test@example.com",
            hashed_password="test",
            google_oauth_sub="google_sub_123",
            is_confirmed=True
        )
        db_session.add(existing_user)
        db_session.commit()
        
        result = OAuthService._find_or_create_google_user(
            db_session, 
            "test@example.com", 
            "google_sub_123"
        )
        
        assert result.id == existing_user.id
        assert result.google_oauth_sub == "google_sub_123"

    def test_find_or_create_link_existing_user_by_email(self, db_session: Session):
        """Test linking existing user by email."""
        # Create existing user without Google sub
        existing_user = User(
            email="test@example.com",
            hashed_password="test",
            is_confirmed=True
        )
        db_session.add(existing_user)
        db_session.commit()
        
        result = OAuthService._find_or_create_google_user(
            db_session, 
            "test@example.com", 
            "google_sub_456"
        )
        
        assert result.id == existing_user.id
        assert result.google_oauth_sub == "google_sub_456"

    def test_find_or_create_new_user(self, db_session: Session):
        """Test creating new user."""
        result = OAuthService._find_or_create_google_user(
            db_session, 
            "newuser@example.com", 
            "google_sub_789"
        )
        
        assert result.email == "newuser@example.com"
        assert result.google_oauth_sub == "google_sub_789"
        assert result.is_confirmed is True
        assert result.hashed_password == ""

    def test_find_or_create_logs_activity(self, db_session: Session):
        """Test that user activity is logged."""
        with patch("app.integrations.user_oauth.create_user_activity_log") as mock_log:
            result = OAuthService._find_or_create_google_user(
                db_session, 
                "newuser@example.com", 
                "google_sub_999"
            )
            
            # Activity logging should be called
            assert mock_log.called

    def test_find_or_create_handles_logging_error(self, db_session: Session):
        """Test that logging errors don't break user creation."""
        with patch("app.integrations.user_oauth.create_user_activity_log") as mock_log:
            mock_log.side_effect = Exception("Logging error")
            
            # Should not raise despite logging error
            result = OAuthService._find_or_create_google_user(
                db_session, 
                "newuser@example.com", 
                "google_sub_000"
            )
            
            assert result.email == "newuser@example.com"


class TestGenerateRedirectURL:
    """Test redirect URL generation based on user agent."""

    def test_generate_redirect_url_for_mobile_android(self):
        """Test redirect URL for Android mobile."""
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.frontend_redirect_url_mobile = "myapp://oauth/callback"
            mock_settings.frontend_redirect_url_web = "http://localhost:3000/dashboard"

            # Use Expo user agent since generate_redirect_url only detects Expo/ReactNative
            result = OAuthService.generate_redirect_url(
                "test_token",
                "Expo Android"
            )

            assert "myapp://oauth/callback" in result
            assert "access_token=test_token" in result

    def test_generate_redirect_url_for_mobile_iphone(self):
        """Test redirect URL for iPhone."""
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.frontend_redirect_url_mobile = "myapp://oauth/callback"
            mock_settings.frontend_redirect_url_web = "http://localhost:3000/dashboard"

            # Use Expo user agent since generate_redirect_url only detects Expo/ReactNative
            result = OAuthService.generate_redirect_url(
                "test_token",
                "Expo iOS"
            )

            assert "myapp://oauth/callback" in result
            assert "access_token=test_token" in result

    def test_generate_redirect_url_for_mobile_expo(self):
        """Test redirect URL for Expo mobile app."""
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.frontend_redirect_url_mobile = "myapp://oauth/callback"
            mock_settings.frontend_redirect_url_web = "http://localhost:3000/dashboard"
            
            result = OAuthService.generate_redirect_url(
                "test_token",
                "Expo/1.0 (iPhone)"
            )
            
            assert "myapp://oauth/callback" in result
            assert "access_token=test_token" in result

    def test_generate_redirect_url_for_web(self):
        """Test redirect URL for web browser."""
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.frontend_redirect_url_mobile = "myapp://oauth/callback"
            mock_settings.frontend_redirect_url_web = "http://localhost:3000/dashboard"
            
            result = OAuthService.generate_redirect_url(
                "test_token",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            )
            
            assert "http://localhost:3000/dashboard" in result
            assert "#access_token=test_token" in result

    def test_generate_redirect_url_for_web_chrome(self):
        """Test redirect URL for Chrome browser."""
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.frontend_redirect_url_mobile = "myapp://oauth/callback"
            mock_settings.frontend_redirect_url_web = "http://localhost:3000/dashboard"
            
            result = OAuthService.generate_redirect_url(
                "test_token",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            
            assert "http://localhost:3000/dashboard" in result
            assert "#access_token=test_token" in result

    def test_generate_redirect_url_case_insensitive(self):
        """Test that user agent detection is case-insensitive."""
        with patch("app.integrations.user_oauth.settings") as mock_settings:
            mock_settings.frontend_redirect_url_mobile = "myapp://oauth/callback"
            mock_settings.frontend_redirect_url_web = "http://localhost:3000/dashboard"

            # Use uppercase EXPO to test case-insensitivity
            result = OAuthService.generate_redirect_url(
                "test_token",
                "EXPO MOBILE APP"
            )

            assert "myapp://oauth/callback" in result
