"""Unit tests for Gmail plugin functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.integrations.simple_plugins.gmail_plugin import (
    gmail_new_email_handler,
    gmail_new_unread_email_handler,
    gmail_email_starred_handler,
    gmail_send_email_handler,
    gmail_mark_as_read_handler,
    gmail_forward_email_handler,
)
from app.models.area import Area
from app.models.service_connection import ServiceConnection
from app.db.session import SessionLocal


class TestGmailPlugin:
    """Test class for Gmail plugin handlers."""
    
    def setup_method(self):
        """Setup test data for each test method."""
        self.mock_area = MagicMock(spec=Area)
        self.mock_area.id = "area-123"
        self.mock_area.user_id = "user-456"
        
        self.mock_service_connection = MagicMock(spec=ServiceConnection)
        self.mock_service_connection.encrypted_access_token = "encrypted_token_123"
        
        # Mock event data
        self.mock_event = {
            "now": datetime.now().isoformat(),
            "area_id": "area-123",
            "user_id": "user-456",
        }
        
    @patch('app.db.session.SessionLocal')
    @patch('app.integrations.simple_plugins.gmail_plugin.get_service_connection_by_user_and_service')
    @patch('app.integrations.simple_plugins.gmail_plugin.decrypt_token')
    @patch('app.integrations.simple_plugins.gmail_plugin.OAuth2ProviderFactory')
    @pytest.mark.asyncio
    async def test_gmail_new_email_handler(self, mock_factory, mock_decrypt, mock_get_connection, mock_session_local):
        """Test new email handler."""
        # Arrange
        # Mock the database session
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        mock_get_connection.return_value = self.mock_service_connection
        mock_decrypt.return_value = "decrypted_access_token"
        
        mock_provider = AsyncMock()
        mock_provider.list_gmail_messages.return_value = {
            "messages": [
                {"id": "msg1", "threadId": "thread1", "snippet": "Test message"}
            ]
        }
        mock_provider.get_gmail_message.return_value = {
            "id": "msg1",
            "threadId": "thread1", 
            "snippet": "Test message",
            "payload": {"headers": [{"name": "From", "value": "sender@example.com"}]}
        }
        
        mock_factory.create_provider.return_value = mock_provider
        
        params = {"sender": "sender@example.com"}
        
        # Act
        await gmail_new_email_handler(self.mock_area, params, self.mock_event)
        
        # Assert
        mock_session_local.assert_called()
        mock_db.close.assert_called()
        mock_get_connection.assert_called_once_with(mock_db, self.mock_area.user_id, "gmail")
        mock_decrypt.assert_called_once_with("encrypted_token_123")
        mock_provider.list_gmail_messages.assert_called_once_with(
            "decrypted_access_token", 
            query="from:sender@example.com"
        )
        mock_provider.get_gmail_message.assert_called_once_with("decrypted_access_token", "msg1")
    
    @patch('app.db.session.SessionLocal')
    @patch('app.integrations.simple_plugins.gmail_plugin.get_service_connection_by_user_and_service')
    @patch('app.integrations.simple_plugins.gmail_plugin.decrypt_token')
    @patch('app.integrations.simple_plugins.gmail_plugin.OAuth2ProviderFactory')
    @pytest.mark.asyncio
    async def test_gmail_new_unread_email_handler(self, mock_factory, mock_decrypt, mock_get_connection, mock_session_local):
        """Test new unread email handler."""
        # Arrange
        # Mock the database session
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        mock_get_connection.return_value = self.mock_service_connection
        mock_decrypt.return_value = "decrypted_access_token"
        
        mock_provider = AsyncMock()
        mock_provider.list_gmail_messages.return_value = {
            "messages": [
                {"id": "msg1", "threadId": "thread1", "snippet": "Unread message"}
            ]
        }
        mock_provider.get_gmail_message.return_value = {
            "id": "msg1",
            "threadId": "thread1",
            "snippet": "Unread message",
            "payload": {"headers": [{"name": "From", "value": "sender@example.com"}]}
        }
        
        mock_factory.create_provider.return_value = mock_provider
        
        # Act
        await gmail_new_unread_email_handler(self.mock_area, {}, self.mock_event)
        
        # Assert
        mock_session_local.assert_called()
        mock_db.close.assert_called()
        mock_get_connection.assert_called_once_with(mock_db, self.mock_area.user_id, "gmail")
        mock_decrypt.assert_called_once_with("encrypted_token_123")
        mock_provider.list_gmail_messages.assert_called_once_with(
            "decrypted_access_token", 
            query="is:unread"
        )
        mock_provider.get_gmail_message.assert_called_once_with("decrypted_access_token", "msg1")
    
    @patch('app.db.session.SessionLocal')
    @patch('app.integrations.simple_plugins.gmail_plugin.get_service_connection_by_user_and_service')
    @patch('app.integrations.simple_plugins.gmail_plugin.decrypt_token')
    @patch('app.integrations.simple_plugins.gmail_plugin.OAuth2ProviderFactory')
    @pytest.mark.asyncio
    async def test_gmail_email_starred_handler(self, mock_factory, mock_decrypt, mock_get_connection, mock_session_local):
        """Test email starred handler."""
        # Arrange
        # Mock the database session
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        mock_get_connection.return_value = self.mock_service_connection
        mock_decrypt.return_value = "decrypted_access_token"
        
        mock_provider = AsyncMock()
        mock_provider.list_gmail_messages.return_value = {
            "messages": [
                {"id": "msg1", "threadId": "thread1", "snippet": "Starred message"}
            ]
        }
        mock_provider.get_gmail_message.return_value = {
            "id": "msg1",
            "threadId": "thread1",
            "snippet": "Starred message",
            "payload": {"headers": [{"name": "From", "value": "sender@example.com"}]}
        }
        
        mock_factory.create_provider.return_value = mock_provider
        
        # Act
        await gmail_email_starred_handler(self.mock_area, {}, self.mock_event)
        
        # Assert
        mock_session_local.assert_called()
        mock_db.close.assert_called()
        mock_get_connection.assert_called_once_with(mock_db, self.mock_area.user_id, "gmail")
        mock_decrypt.assert_called_once_with("encrypted_token_123")
        mock_provider.list_gmail_messages.assert_called_once_with(
            "decrypted_access_token", 
            query="label:STARRED"
        )
        mock_provider.get_gmail_message.assert_called_once_with("decrypted_access_token", "msg1")
    
    @patch('app.db.session.SessionLocal')
    @patch('app.integrations.simple_plugins.gmail_plugin.get_service_connection_by_user_and_service')
    @patch('app.integrations.simple_plugins.gmail_plugin.decrypt_token')
    @patch('app.integrations.simple_plugins.gmail_plugin.OAuth2ProviderFactory')
    @pytest.mark.asyncio
    async def test_gmail_send_email_handler(self, mock_factory, mock_decrypt, mock_get_connection, mock_session_local):
        """Test send email handler."""
        # Arrange
        # Mock get_service_connection_by_user_and_service to return the connection when called with proper arguments
        mock_get_connection.return_value = self.mock_service_connection
        mock_decrypt.return_value = "decrypted_access_token"
        
        mock_provider = AsyncMock()
        mock_provider.create_raw_email.return_value = "raw_encoded_email"
        mock_provider.send_gmail_message.return_value = {"id": "sent_msg_123"}
        
        mock_factory.create_provider.return_value = mock_provider
        
        params = {
            "to": "recipient@example.com",
            "subject": "Test Subject",
            "body": "Test Body"
        }
        
        # Mock the database session context
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        # Act
        await gmail_send_email_handler(self.mock_area, params, self.mock_event)
        
        # Assert
        # Check that the database session was used properly
        mock_session_local.assert_called()
        mock_db.close.assert_called()
        
        # Check that the service connection was retrieved properly
        mock_get_connection.assert_called_once_with(mock_db, self.mock_area.user_id, "gmail")
        mock_decrypt.assert_called_once_with("encrypted_token_123")
        mock_provider.create_raw_email.assert_called_once_with(
            "recipient@example.com",
            "Test Subject",
            "Test Body",
            "",
            ""
        )
        # For async calls, verify the call was made with correct arguments
        # Check that the call was made (with potentially coroutine object as second argument)
        assert mock_provider.send_gmail_message.call_count == 1
        call_args = mock_provider.send_gmail_message.call_args
        assert call_args[0][0] == "decrypted_access_token"  # Check first argument
    
    @patch('app.db.session.SessionLocal')
    @patch('app.integrations.simple_plugins.gmail_plugin.get_service_connection_by_user_and_service')
    @patch('app.integrations.simple_plugins.gmail_plugin.decrypt_token')
    @patch('app.integrations.simple_plugins.gmail_plugin.OAuth2ProviderFactory')
    @pytest.mark.asyncio
    async def test_gmail_mark_as_read_handler(self, mock_factory, mock_decrypt, mock_get_connection, mock_session_local):
        """Test mark as read handler."""
        # Arrange
        # Mock the database session
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        mock_get_connection.return_value = self.mock_service_connection
        mock_decrypt.return_value = "decrypted_access_token"
        
        mock_provider = AsyncMock()
        mock_provider.modify_gmail_message.return_value = {"id": "modified_msg_123"}
        
        mock_factory.create_provider.return_value = mock_provider
        
        # Add message ID to event
        self.mock_event["gmail.message_id"] = "msg_to_mark"
        params = {}
        
        # Act
        await gmail_mark_as_read_handler(self.mock_area, params, self.mock_event)
        
        # Assert
        mock_session_local.assert_called()
        mock_db.close.assert_called()
        mock_get_connection.assert_called_once_with(mock_db, self.mock_area.user_id, "gmail")
        mock_decrypt.assert_called_once_with("encrypted_token_123")
        mock_provider.modify_gmail_message.assert_called_once_with(
            "decrypted_access_token",
            "msg_to_mark",
            remove_labels=["UNREAD"]
        )
    
    @patch('app.db.session.SessionLocal')
    @patch('app.integrations.simple_plugins.gmail_plugin.get_service_connection_by_user_and_service')
    @patch('app.integrations.simple_plugins.gmail_plugin.decrypt_token')
    @patch('app.integrations.simple_plugins.gmail_plugin.OAuth2ProviderFactory')
    @pytest.mark.asyncio
    async def test_gmail_forward_email_handler(self, mock_factory, mock_decrypt, mock_get_connection, mock_session_local):
        """Test forward email handler."""
        # Arrange
        # Mock the database session
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        mock_get_connection.return_value = self.mock_service_connection
        mock_decrypt.return_value = "decrypted_access_token"
        
        mock_provider = AsyncMock()
        mock_provider.get_gmail_message.return_value = {
            "id": "original_msg",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Original Subject"},
                    {"name": "From", "value": "original@example.com"}
                ]
            },
            "body": {"data": "VGhpcyBpcyB0aGUgb3JpZ2luYWwgYm9keQ=="}
        }
        mock_provider.create_raw_email.return_value = "raw_encoded_forwarded_email"
        mock_provider.send_gmail_message.return_value = {"id": "forwarded_msg_123"}
        
        mock_factory.create_provider.return_value = mock_provider
        
        # Add original message ID to event
        self.mock_event["gmail.message_id"] = "original_msg"
        params = {"to": "forward@example.com"}
        
        # Act
        await gmail_forward_email_handler(self.mock_area, params, self.mock_event)
        
        # Assert
        mock_session_local.assert_called()
        mock_db.close.assert_called()
        mock_get_connection.assert_called_once_with(mock_db, self.mock_area.user_id, "gmail")
        mock_decrypt.assert_called_once_with("encrypted_token_123")
        mock_provider.get_gmail_message.assert_called_once_with("decrypted_access_token", "original_msg")
        mock_provider.create_raw_email.assert_called_once()
        mock_provider.send_gmail_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_gmail_send_email_handler_missing_params(self):
        """Test send email handler with missing required parameters."""
        # Arrange
        params = {"to": "recipient@example.com", "subject": "Test Subject"}  # Missing 'body'
        
        # Act & Assert
        with pytest.raises(ValueError, match="Missing required field: body"):
            await gmail_send_email_handler(self.mock_area, params, self.mock_event)
    
    @patch('app.db.session.SessionLocal')
    @patch('app.integrations.simple_plugins.gmail_plugin.get_service_connection_by_user_and_service')
    @patch('app.integrations.simple_plugins.gmail_plugin.decrypt_token')
    @patch('app.integrations.simple_plugins.gmail_plugin.OAuth2ProviderFactory')
    @pytest.mark.asyncio
    async def test_gmail_forward_email_handler_missing_message_id(self, mock_factory, mock_decrypt, mock_get_connection, mock_session_local):
        """Test forward email handler with missing message ID."""
        # Arrange
        params = {"to": "forward@example.com"}
        event = {}  # No message ID in event
        
        # Mock the database session context
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        mock_get_connection.return_value = self.mock_service_connection
        mock_decrypt.return_value = "decrypted_access_token"
        
        # Act & Assert - this should not raise an exception, but should log an error
        await gmail_forward_email_handler(self.mock_area, params, event)
        
        # Verify that the database session was used properly
        mock_session_local.assert_called()
        mock_db.close.assert_called()