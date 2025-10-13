"""Integration tests for API key connection endpoints."""

import pytest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.service_connection import ServiceConnection
from app.db.session import engine
from app.core.encryption import encrypt_token
from app.core.config import settings
from tests.conftest import SyncASGITestClient


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
    
    def test_add_api_key_connection_success(self, client: SyncASGITestClient, auth_token: str, valid_api_key: str):
        """Test successful addition of an API key connection."""
        # Mock the OpenAI API validation
        with patch("httpx.AsyncClient") as mock_httpx_client_class:
            # Create a mock client instance
            mock_client_instance = AsyncMock()
            mock_httpx_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            # Mock the response
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client_instance.get.return_value = mock_response
            
            response = client.post(
                "/api/v1/service-connections/api-key/openai",
                json={"api_key": valid_api_key},
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Successfully added openai API key"
            assert data["provider"] == "openai"
            assert "connection_id" in data
    
    def test_add_api_key_connection_invalid_format(self, client: SyncASGITestClient, auth_token: str):
        """Test adding API key with invalid format."""
        invalid_key = "invalid-key-format"
        
        response = client.post(
            "/api/v1/service-connections/api-key/openai",
            json={"api_key": invalid_key},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Pydantic validation errors return 422
        assert response.status_code == 422
        # Check if the error message mentions invalid format
        response_data = response.json()
        assert "detail" in response_data
    
    def test_add_api_key_connection_invalid_key(self, client: SyncASGITestClient, auth_token: str, valid_api_key: str):
        """Test adding an API key that fails OpenAI validation."""
        # Mock the OpenAI API validation to fail
        with patch("httpx.AsyncClient") as mock_httpx_client_class:
            # Create a mock client instance
            mock_client_instance = AsyncMock()
            mock_httpx_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            # Mock the response with 401 error
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_client_instance.get.return_value = mock_response
            
            response = client.post(
                "/api/v1/service-connections/api-key/openai",
                json={"api_key": valid_api_key},
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            
            assert response.status_code == 400
            assert "Invalid API key" in response.json()["detail"] or "Authentication failed" in response.json()["detail"]
    
    def test_add_api_key_connection_duplicate(self, client: SyncASGITestClient, auth_token: str, valid_api_key: str, db_session: Session):
        """Test adding an API key when one already exists for the service."""
        # First, create a connection successfully
        with patch("httpx.AsyncClient") as mock_httpx_client_class:
            # Create a mock client instance
            mock_client_instance = AsyncMock()
            mock_httpx_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            # Mock the response
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client_instance.get.return_value = mock_response
            
            # First request should succeed
            response1 = client.post(
                "/api/v1/service-connections/api-key/openai",
                json={"api_key": valid_api_key},
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            assert response1.status_code == 200
            
            # Second request should fail with duplicate error
            response2 = client.post(
                "/api/v1/service-connections/api-key/openai",
                json={"api_key": valid_api_key},
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            
            assert response2.status_code == 409
            assert "already exists" in response2.json()["detail"]
    
    def test_add_api_key_connection_unsupported_provider(self, client: SyncASGITestClient, auth_token: str, valid_api_key: str):
        """Test adding an API key for an unsupported provider."""
        response = client.post(
            "/api/v1/service-connections/api-key/unsupported-provider",
            json={"api_key": valid_api_key},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 400
        assert "API key connection not supported" in response.json()["detail"]
    
    def test_add_api_key_connection_missing_key(self, client: SyncASGITestClient, auth_token: str):
        """Test adding an API key with missing key in request."""
        response = client.post(
            "/api/v1/service-connections/api-key/openai",
            json={},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_add_api_key_connection_unauthorized(self, client: SyncASGITestClient):
        """Test adding an API key without authentication."""
        response = client.post(
            "/api/v1/service-connections/api-key/openai",
            json={"api_key": "sk-test1234567890abcdefghijklmnop"}
        )
        
        assert response.status_code == 401  # Unauthorized
    
    def test_add_api_key_connection_success_proj_format(self, client: SyncASGITestClient, auth_token: str, valid_api_key_proj: str):
        """Test successful addition of an API key connection with project-based format."""
        # Mock the OpenAI API validation
        with patch("httpx.AsyncClient") as mock_httpx_client_class:
            # Create a mock client instance
            mock_client_instance = AsyncMock()
            mock_httpx_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            # Mock the response
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client_instance.get.return_value = mock_response
            
            response = client.post(
                "/api/v1/service-connections/api-key/openai",
                json={"api_key": valid_api_key_proj},
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Successfully added openai API key"
            assert data["provider"] == "openai"
            assert "connection_id" in data
    
    def test_add_api_key_connection_success_svcacct_format(self, client: SyncASGITestClient, auth_token: str, valid_api_key_svcacct: str):
        """Test successful addition of an API key connection with service account format."""
        # Mock the OpenAI API validation
        with patch("httpx.AsyncClient") as mock_httpx_client_class:
            # Create a mock client instance
            mock_client_instance = AsyncMock()
            mock_httpx_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            # Mock the response
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client_instance.get.return_value = mock_response
            
            response = client.post(
                "/api/v1/service-connections/api-key/openai",
                json={"api_key": valid_api_key_svcacct},
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Successfully added openai API key"
            assert data["provider"] == "openai"
            assert "connection_id" in data