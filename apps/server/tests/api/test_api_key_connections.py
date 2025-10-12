"""Integration tests for API key connection endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.service_connection import ServiceConnection
from app.db.session import engine
from app.core.encryption import encrypt_token
from app.core.config import settings
from main import app


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(app)


@pytest.fixture
def test_user():
    """Create a test user."""
    user = User()
    user.id = "test-user-id"
    user.email = "test@example.com"
    user.hashed_password = "hashed_password"
    user.is_active = True
    user.is_verified = True
    return user


@pytest.fixture
def valid_api_key():
    """Return a valid OpenAI API key format."""
    return "sk-test1234567890abcdefghijklmnop"


@pytest.fixture
def valid_api_key_proj():
    """Return a valid OpenAI project-based API key format."""
    return "sk-proj-test1234567890abcdefghijklmnop"


@pytest.fixture
def valid_api_key_svcacct():
    """Return a valid OpenAI service account API key format."""
    return "sk-svcacct-test1234567890abcdefghijklmnop"


class TestApiKeyConnectionEndpoints:
    
    def test_add_api_key_connection_success(self, client, test_user, valid_api_key):
        """Test successful addition of an API key connection."""
        # Mock the OpenAI API validation
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value.__aenter__.return_value = AsyncMock()
            mock_post.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # Mock database operations
            with patch("app.api.routes.service_connections.get_service_connection_by_user_and_service", 
                      return_value=None), \
                 patch("app.api.routes.service_connections.encrypt_token", 
                      return_value=encrypt_token(valid_api_key)), \
                 patch("app.services.user_activity_logs.log_user_activity_task") as mock_log_task:
                
                # Mock session for database
                with patch("app.api.dependencies.get_db") as mock_db_session:
                    mock_db = MagicMock(spec=Session)
                    mock_db_session.return_value.__enter__.return_value = mock_db
                    
                    # Mock the user authentication dependency
                    with patch("app.api.dependencies.require_active_user", return_value=test_user):
                        response = client.post(
                            "/api/v1/service-connections/api-key/openai",
                            json={"api_key": valid_api_key},
                            headers={"Authorization": f"Bearer test-token"}
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert data["message"] == "Successfully added openai API key"
                        assert data["provider"] == "openai"
                        assert "connection_id" in data
    
    def test_add_api_key_connection_invalid_format(self, client, test_user):
        """Test adding API key with invalid format."""
        invalid_key = "invalid-key-format"
        
        # Mock the user authentication dependency
        with patch("app.api.dependencies.require_active_user", return_value=test_user):
            response = client.post(
                "/api/v1/service-connections/api-key/openai",
                json={"api_key": invalid_key},
                headers={"Authorization": f"Bearer test-token"}
            )
            
            assert response.status_code == 400
            assert "Invalid API key format" in response.json()["detail"]
    
    def test_add_api_key_connection_invalid_key(self, client, test_user, valid_api_key):
        """Test adding an API key that fails OpenAI validation."""
        # Mock the OpenAI API validation to fail
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_post.return_value.__aenter__.return_value = AsyncMock()
            mock_post.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # Mock the user authentication dependency
            with patch("app.api.dependencies.require_active_user", return_value=test_user):
                response = client.post(
                    "/api/v1/service-connections/api-key/openai",
                    json={"api_key": valid_api_key},
                    headers={"Authorization": f"Bearer test-token"}
                )
                
                assert response.status_code == 400
                assert "Invalid API key" in response.json()["detail"]
    
    def test_add_api_key_connection_duplicate(self, client, test_user, valid_api_key):
        """Test adding an API key when one already exists for the service."""
        # Mock to simulate existing connection
        with patch("app.api.routes.service_connections.get_service_connection_by_user_and_service") as mock_get_conn:
            mock_existing_conn = MagicMock(spec=ServiceConnection)
            mock_get_conn.return_value = mock_existing_conn
            
            # Mock the user authentication dependency
            with patch("app.api.dependencies.require_active_user", return_value=test_user):
                response = client.post(
                    "/api/v1/service-connections/api-key/openai",
                    json={"api_key": valid_api_key},
                    headers={"Authorization": f"Bearer test-token"}
                )
                
                assert response.status_code == 409
                assert "already exists" in response.json()["detail"]
    
    def test_add_api_key_connection_unsupported_provider(self, client, test_user, valid_api_key):
        """Test adding an API key for an unsupported provider."""
        # Mock the user authentication dependency
        with patch("app.api.dependencies.require_active_user", return_value=test_user):
            response = client.post(
                "/api/v1/service-connections/api-key/unsupported-provider",
                json={"api_key": valid_api_key},
                headers={"Authorization": f"Bearer test-token"}
            )
            
            assert response.status_code == 400
            assert "API key connection not supported" in response.json()["detail"]
    
    def test_add_api_key_connection_missing_key(self, client, test_user):
        """Test adding an API key with missing key in request."""
        # Mock the user authentication dependency
        with patch("app.api.dependencies.require_active_user", return_value=test_user):
            response = client.post(
                "/api/v1/service-connections/api-key/openai",
                json={},
                headers={"Authorization": f"Bearer test-token"}
            )
            
            assert response.status_code == 422  # Validation error
    
    def test_add_api_key_connection_unauthorized(self, client):
        """Test adding an API key without authentication."""
        response = client.post(
            "/api/v1/service-connections/api-key/openai",
            json={"api_key": "sk-test1234567890abcdefghijklmnop"}
        )
        
        assert response.status_code == 401  # Unauthorized
    
    def test_add_api_key_connection_success_proj_format(self, client, test_user, valid_api_key_proj):
        """Test successful addition of an API key connection with project-based format."""
        # Mock the OpenAI API validation
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value.__aenter__.return_value = AsyncMock()
            mock_post.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # Mock database operations
            with patch("app.api.routes.service_connections.get_service_connection_by_user_and_service", 
                      return_value=None), \
                 patch("app.api.routes.service_connections.encrypt_token", 
                      return_value=encrypt_token(valid_api_key_proj)), \
                 patch("app.services.user_activity_logs.log_user_activity_task") as mock_log_task:
                
                # Mock session for database
                with patch("app.api.dependencies.get_db") as mock_db_session:
                    mock_db = MagicMock(spec=Session)
                    mock_db_session.return_value.__enter__.return_value = mock_db
                    
                    # Mock the user authentication dependency
                    with patch("app.api.dependencies.require_active_user", return_value=test_user):
                        response = client.post(
                            "/api/v1/service-connections/api-key/openai",
                            json={"api_key": valid_api_key_proj},
                            headers={"Authorization": f"Bearer test-token"}
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert data["message"] == "Successfully added openai API key"
                        assert data["provider"] == "openai"
                        assert "connection_id" in data
    
    def test_add_api_key_connection_success_svcacct_format(self, client, test_user, valid_api_key_svcacct):
        """Test successful addition of an API key connection with service account format."""
        # Mock the OpenAI API validation
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value.__aenter__.return_value = AsyncMock()
            mock_post.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # Mock database operations
            with patch("app.api.routes.service_connections.get_service_connection_by_user_and_service", 
                      return_value=None), \
                 patch("app.api.routes.service_connections.encrypt_token", 
                      return_value=encrypt_token(valid_api_key_svcacct)), \
                 patch("app.services.user_activity_logs.log_user_activity_task") as mock_log_task:
                
                # Mock session for database
                with patch("app.api.dependencies.get_db") as mock_db_session:
                    mock_db = MagicMock(spec=Session)
                    mock_db_session.return_value.__enter__.return_value = mock_db
                    
                    # Mock the user authentication dependency
                    with patch("app.api.dependencies.require_active_user", return_value=test_user):
                        response = client.post(
                            "/api/v1/service-connections/api-key/openai",
                            json={"api_key": valid_api_key_svcacct},
                            headers={"Authorization": f"Bearer test-token"}
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert data["message"] == "Successfully added openai API key"
                        assert data["provider"] == "openai"
                        assert "connection_id" in data