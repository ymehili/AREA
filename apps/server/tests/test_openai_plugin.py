"""Unit tests for OpenAI plugin functions."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.orm import Session

from app.integrations.simple_plugins.openai_plugin import (
    chat_completion_handler,
    text_completion_handler,
    image_generation_handler,
    content_moderation_handler,
)
from app.models.area import Area
from app.models.service_connection import ServiceConnection
from app.integrations.simple_plugins.exceptions import OpenAIConnectionError, OpenAIAPIError


class TestOpenAIPlugin:
    
    @pytest.fixture
    def area(self):
        """Create a mock area object for testing."""
        area = Area()
        area.id = "test-area-id"
        area.name = "Test Area"
        area.user_id = "test-user-id"
        return area
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return MagicMock(spec=Session)
    
    @pytest.fixture
    def mock_service_connection(self):
        """Create a mock service connection."""
        connection = ServiceConnection()
        connection.encrypted_access_token = "encrypted_test_key"
        return connection
    
    def test_get_openai_client_success(self, area, mock_db, mock_service_connection):
        """Test successful retrieval of OpenAI client."""
        with patch('app.integrations.simple_plugins.openai_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_service_connection), \
             patch('app.integrations.simple_plugins.openai_plugin.decrypt_token',
                   return_value="test_api_key"), \
             patch('httpx.Client') as mock_client_class:
            
            mock_client_instance = MagicMock()
            mock_client_class.return_value = mock_client_instance
            
            from app.integrations.simple_plugins.openai_plugin import _get_openai_client
            client = _get_openai_client(area, mock_db)
            
            # Verify client was created with proper headers
            mock_client_class.assert_called_once_with(
                headers={
                    "Authorization": "Bearer test_api_key",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
    
    def test_get_openai_client_no_connection(self, area, mock_db):
        """Test failure when no service connection exists."""
        with patch('app.integrations.simple_plugins.openai_plugin.get_service_connection_by_user_and_service',
                   return_value=None):
            
            from app.integrations.simple_plugins.openai_plugin import _get_openai_client
            
            with pytest.raises(OpenAIConnectionError):
                _get_openai_client(area, mock_db)
    
    def test_get_openai_client_invalid_key(self, area, mock_db, mock_service_connection):
        """Test failure when API key is invalid."""
        with patch('app.integrations.simple_plugins.openai_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_service_connection), \
             patch('app.integrations.simple_plugins.openai_plugin.decrypt_token',
                   return_value=""):
            
            from app.integrations.simple_plugins.openai_plugin import _get_openai_client
            
            with pytest.raises(OpenAIConnectionError):
                _get_openai_client(area, mock_db)
    
    def test_chat_completion_handler_success(self, area, mock_db):
        """Test successful chat completion."""
        params = {
            "prompt": "Hello, how are you?",
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 100
        }
        event = {}
        
        with patch('app.integrations.simple_plugins.openai_plugin._get_openai_client') as mock_get_client, \
             patch('sqlalchemy.orm.Session') as mock_session_class:
            
            mock_session_instance = MagicMock()
            mock_session_class.return_value = mock_session_instance
            
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            
            # Mock API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [
                    {"message": {"content": "I'm doing well, thank you!"}, "finish_reason": "stop"}
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }
            mock_client.post.return_value = mock_response
            
            # Call the handler
            chat_completion_handler(area, params, event)
            
            # Verify API call
            mock_client.post.assert_called_once_with(
                "https://api.openai.com/v1/chat/completions",
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": "Hello, how are you?"}],
                    "temperature": 0.7,
                    "max_tokens": 100
                }
            )
            
            # Verify event data
            assert event["openai.response"] == "I'm doing well, thank you!"
            assert event["openai.finish_reason"] == "stop"
            assert event["openai.model"] == "gpt-3.5-turbo"
            assert event["openai.input_tokens"] == 10
            assert event["openai.output_tokens"] == 20
    
    def test_chat_completion_handler_api_error(self, area, mock_db):
        """Test chat completion with API error."""
        params = {
            "prompt": "Hello, how are you?",
            "model": "gpt-3.5-turbo"
        }
        event = {}
        
        with patch('app.integrations.simple_plugins.openai_plugin._get_openai_client') as mock_get_client, \
             patch('sqlalchemy.orm.Session') as mock_session_class:
            
            mock_session_instance = MagicMock()
            mock_session_class.return_value = mock_session_instance
            
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            
            # Mock error response
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Invalid API key"
            mock_client.post.return_value = mock_response
            
            # Call the handler should raise OpenAIAPIError
            with pytest.raises(OpenAIAPIError):
                chat_completion_handler(area, params, event)
    
    def test_text_completion_handler_success(self, area):
        """Test successful text completion."""
        params = {
            "prompt": "Complete this sentence: Today is",
            "model": "text-davinci-003",
            "temperature": 0.5,
            "max_tokens": 50
        }
        event = {}
        
        with patch('app.integrations.simple_plugins.openai_plugin._get_openai_client') as mock_get_client, \
             patch('sqlalchemy.orm.Session') as mock_session_class:
            
            mock_session_instance = MagicMock()
            mock_session_class.return_value = mock_session_instance
            
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            
            # Mock API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [
                    {"text": " a beautiful day!", "finish_reason": "stop"}
                ],
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 10,
                    "total_tokens": 15
                }
            }
            mock_client.post.return_value = mock_response
            
            # Call the handler
            text_completion_handler(area, params, event)
            
            # Verify API call
            mock_client.post.assert_called_once_with(
                "https://api.openai.com/v1/completions",
                json={
                    "model": "text-davinci-003",
                    "prompt": "Complete this sentence: Today is",
                    "temperature": 0.5,
                    "max_tokens": 50
                }
            )
            
            # Verify event data
            assert event["openai.response"] == " a beautiful day!"
            assert event["openai.finish_reason"] == "stop"
            assert event["openai.model"] == "text-davinci-003"
    
    def test_image_generation_handler_success(self, area):
        """Test successful image generation."""
        params = {
            "prompt": "A cute cat playing with a ball",
            "n": 1,
            "size": "256x256"
        }
        event = {}
        
        with patch('app.integrations.simple_plugins.openai_plugin._get_openai_client') as mock_get_client, \
             patch('sqlalchemy.orm.Session') as mock_session_class:
            
            mock_session_instance = MagicMock()
            mock_session_class.return_value = mock_session_instance
            
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            
            # Mock API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [
                    {"url": "https://example.com/image1.png"}
                ]
            }
            mock_client.post.return_value = mock_response
            
            # Call the handler
            image_generation_handler(area, params, event)
            
            # Verify API call
            mock_client.post.assert_called_once_with(
                "https://api.openai.com/v1/images/generations",
                json={
                    "prompt": "A cute cat playing with a ball",
                    "n": 1,
                    "size": "256x256",
                    "response_format": "url"
                }
            )
            
            # Verify event data
            assert event["openai.image_urls"] == ["https://example.com/image1.png"]
            assert event["openai.num_images"] == 1
    
    def test_content_moderation_handler_success(self, area):
        """Test successful content moderation."""
        params = {
            "input": "This is a test content"
        }
        event = {}
        
        with patch('app.integrations.simple_plugins.openai_plugin._get_openai_client') as mock_get_client, \
             patch('sqlalchemy.orm.Session') as mock_session_class:
            
            mock_session_instance = MagicMock()
            mock_session_class.return_value = mock_session_instance
            
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            
            # Mock API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [{
                    "categories": {"hate": False, "self-harm": False},
                    "category_scores": {"hate": 0.1, "self-harm": 0.2},
                    "flagged": False
                }]
            }
            mock_client.post.return_value = mock_response
            
            # Call the handler
            content_moderation_handler(area, params, event)
            
            # Verify API call
            mock_client.post.assert_called_once_with(
                "https://api.openai.com/v1/moderations",
                json={
                    "input": "This is a test content",
                    "model": "text-moderation-latest"
                }
            )
            
            # Verify event data
            assert event["openai.moderation.flagged"] is False
            assert event["openai.moderation.categories"] == {"hate": False, "self-harm": False}
    
    def test_missing_prompt_error(self, area):
        """Test error when required parameters are missing."""
        params = {}  # Missing required 'prompt'
        event = {}
        
        with pytest.raises(ValueError):
            text_completion_handler(area, params, event)