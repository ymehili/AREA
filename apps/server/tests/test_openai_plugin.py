"""Unit tests for OpenAI plugin functions."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.orm import Session

from app.integrations.simple_plugins.openai_plugin import (
    _get_openai_api_key,
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
        import uuid
        area = Area()
        area.id = uuid.uuid4()
        area.name = "Test Area"
        area.user_id = uuid.uuid4()
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
    
    def test_get_openai_api_key_success(self, area, mock_db, mock_service_connection):
        """Test successful retrieval of OpenAI API key."""
        with patch('app.integrations.simple_plugins.openai_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_service_connection), \
             patch('app.integrations.simple_plugins.openai_plugin.decrypt_token',
                   return_value="test_api_key"):
            
            api_key = _get_openai_api_key(area, mock_db)
            
            assert api_key == "test_api_key"
    
    def test_get_openai_api_key_no_connection(self, area, mock_db):
        """Test failure when no service connection exists."""
        with patch('app.integrations.simple_plugins.openai_plugin.get_service_connection_by_user_and_service',
                   return_value=None):
            
            with pytest.raises(OpenAIConnectionError, match="OpenAI service connection not found"):
                _get_openai_api_key(area, mock_db)
    
    def test_get_openai_api_key_invalid_key(self, area, mock_db, mock_service_connection):
        """Test failure when API key is invalid."""
        with patch('app.integrations.simple_plugins.openai_plugin.get_service_connection_by_user_and_service',
                   return_value=mock_service_connection), \
             patch('app.integrations.simple_plugins.openai_plugin.decrypt_token',
                   return_value=""):
            
            with pytest.raises(OpenAIConnectionError, match="OpenAI API key not available or invalid"):
                _get_openai_api_key(area, mock_db)
    
    def test_chat_completion_handler_success(self, area):
        """Test successful chat completion."""
        params = {
            "prompt": "Hello, how are you?",
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 100
        }
        event = {}
        
        mock_db = MagicMock()
        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"
        
        with patch('app.integrations.simple_plugins.openai_plugin.SessionLocal', return_value=mock_db):
            with patch('app.integrations.simple_plugins.openai_plugin.get_service_connection_by_user_and_service', return_value=mock_connection):
                with patch('app.integrations.simple_plugins.openai_plugin.decrypt_token', return_value="test_api_key"):
                    with patch('httpx.Client') as mock_client_class:
                        # Mock the context manager
                        mock_client = MagicMock()
                        mock_client_class.return_value.__enter__.return_value = mock_client
                        mock_client_class.return_value.__exit__.return_value = None
                        
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
                        
                        # Verify the response was stored in event
                        assert event["openai.response"] == "I'm doing well, thank you!"
                        assert event["openai.finish_reason"] == "stop"
                        assert event["openai.input_tokens"] == 10
                        assert event["openai.output_tokens"] == 20
                        assert event["openai.total_tokens"] == 30
                        
                        # Verify DB session was closed
                        mock_db.close.assert_called_once()
    
    def test_chat_completion_handler_api_error(self, area):
        """Test chat completion with API error."""
        params = {
            "prompt": "Hello, how are you?",
            "model": "gpt-3.5-turbo"
        }
        event = {}
        
        mock_db = MagicMock()
        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"
        
        with patch('app.integrations.simple_plugins.openai_plugin.SessionLocal', return_value=mock_db):
            with patch('app.integrations.simple_plugins.openai_plugin.get_service_connection_by_user_and_service', return_value=mock_connection):
                with patch('app.integrations.simple_plugins.openai_plugin.decrypt_token', return_value="test_api_key"):
                    with patch('httpx.Client') as mock_client_class:
                        # Mock the context manager
                        mock_client = MagicMock()
                        mock_client_class.return_value.__enter__.return_value = mock_client
                        mock_client_class.return_value.__exit__.return_value = None
                        
                        # Mock error response
                        mock_response = MagicMock()
                        mock_response.status_code = 401
                        mock_response.text = "Invalid API key"
                        mock_client.post.return_value = mock_response
                        
                        # Call the handler should raise OpenAIAPIError
                        with pytest.raises(OpenAIAPIError):
                            chat_completion_handler(area, params, event)
                        
                        # Verify DB session was closed
                        mock_db.close.assert_called_once()
    
    def test_text_completion_handler_success(self, area):
        """Test successful text completion."""
        params = {
            "prompt": "Complete this sentence: Today is",
            "model": "gpt-3.5-turbo-instruct",
            "temperature": 0.5,
            "max_tokens": 50
        }
        event = {}
        
        mock_db = MagicMock()
        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"
        
        with patch('app.integrations.simple_plugins.openai_plugin.SessionLocal', return_value=mock_db):
            with patch('app.integrations.simple_plugins.openai_plugin.get_service_connection_by_user_and_service', return_value=mock_connection):
                with patch('app.integrations.simple_plugins.openai_plugin.decrypt_token', return_value="test_api_key"):
                    with patch('httpx.Client') as mock_client_class:
                        # Mock the context manager
                        mock_client = MagicMock()
                        mock_client_class.return_value.__enter__.return_value = mock_client
                        mock_client_class.return_value.__exit__.return_value = None
                        
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
                        
                        # Verify event data
                        assert event["openai.response"] == " a beautiful day!"
                        assert event["openai.finish_reason"] == "stop"
                        assert event["openai.model"] == "gpt-3.5-turbo-instruct"
                        
                        # Verify DB session was closed
                        mock_db.close.assert_called_once()
    
    def test_image_generation_handler_success(self, area):
        """Test successful image generation."""
        params = {
            "prompt": "A cute cat playing with a ball",
            "n": 1,
            "size": "256x256"
        }
        event = {}
        
        mock_db = MagicMock()
        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"
        
        with patch('app.integrations.simple_plugins.openai_plugin.SessionLocal', return_value=mock_db):
            with patch('app.integrations.simple_plugins.openai_plugin.get_service_connection_by_user_and_service', return_value=mock_connection):
                with patch('app.integrations.simple_plugins.openai_plugin.decrypt_token', return_value="test_api_key"):
                    with patch('httpx.Client') as mock_client_class:
                        # Mock the context manager
                        mock_client = MagicMock()
                        mock_client_class.return_value.__enter__.return_value = mock_client
                        mock_client_class.return_value.__exit__.return_value = None
                        
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
                        
                        # Verify event data
                        assert event["openai.image_urls"] == ["https://example.com/image1.png"]
                        assert event["openai.num_images"] == 1
                        
                        # Verify DB session was closed
                        mock_db.close.assert_called_once()
    
    def test_content_moderation_handler_success(self, area):
        """Test successful content moderation."""
        params = {
            "input": "This is a test content"
        }
        event = {}
        
        mock_db = MagicMock()
        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"
        
        with patch('app.integrations.simple_plugins.openai_plugin.SessionLocal', return_value=mock_db):
            with patch('app.integrations.simple_plugins.openai_plugin.get_service_connection_by_user_and_service', return_value=mock_connection):
                with patch('app.integrations.simple_plugins.openai_plugin.decrypt_token', return_value="test_api_key"):
                    with patch('httpx.Client') as mock_client_class:
                        # Mock the context manager
                        mock_client = MagicMock()
                        mock_client_class.return_value.__enter__.return_value = mock_client
                        mock_client_class.return_value.__exit__.return_value = None
                        
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
                        
                        # Verify event data
                        assert event["openai.moderation.flagged"] is False
                        assert event["openai.moderation.categories"] == {"hate": False, "self-harm": False}
                        
                        # Verify DB session was closed
                        mock_db.close.assert_called_once()
    
    def test_missing_prompt_error(self, area):
        """Test error when required parameters are missing."""
        params = {}  # Missing required 'prompt'
        event = {}
        
        with pytest.raises(ValueError):
            text_completion_handler(area, params, event)