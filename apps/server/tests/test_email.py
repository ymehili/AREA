"""Tests for email service."""

from __future__ import annotations

from email.message import EmailMessage
from unittest.mock import MagicMock, patch
import smtplib

import pytest

from app.services.email import (
    EmailDeliveryError,
    build_confirmation_email,
    send_confirmation_email,
    send_email,
)


def test_build_confirmation_email() -> None:
    """Test building a confirmation email message."""
    recipient = "test@example.com"
    confirmation_link = "https://example.com/confirm?token=abc123"
    
    message = build_confirmation_email(recipient, confirmation_link)
    
    assert isinstance(message, EmailMessage)
    assert message["To"] == recipient
    assert message["Subject"] == "Confirm your Action-Reaction account"
    # Check in the text/plain part
    assert confirmation_link in str(message)
    

def test_send_email_success() -> None:
    """Test sending an email successfully."""
    message = EmailMessage()
    message["Subject"] = "Test"
    message["From"] = "sender@example.com"
    message["To"] = "recipient@example.com"
    message.set_content("Test content")
    
    with patch("smtplib.SMTP") as mock_smtp_class:
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp
        
        send_email(message)
        
        # Verify SMTP was configured correctly
        mock_smtp.send_message.assert_called_once_with(message)


def test_send_email_with_tls() -> None:
    """Test sending an email with TLS enabled."""
    message = EmailMessage()
    message["Subject"] = "Test"
    message["From"] = "sender@example.com"
    message["To"] = "recipient@example.com"
    message.set_content("Test content")
    
    with patch("smtplib.SMTP") as mock_smtp_class:
        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.smtp_use_tls = True
            
            mock_smtp = MagicMock()
            mock_smtp_class.return_value.__enter__.return_value = mock_smtp
            
            send_email(message)
            
            # Verify TLS was started
            mock_smtp.starttls.assert_called_once()
            # Verify authentication was performed
            mock_smtp.login.assert_called_once_with("user", "pass")
            mock_smtp.send_message.assert_called_once_with(message)


def test_send_email_without_auth() -> None:
    """Test sending an email without authentication."""
    message = EmailMessage()
    message["Subject"] = "Test"
    message["From"] = "sender@example.com"
    message["To"] = "recipient@example.com"
    message.set_content("Test content")
    
    with patch("smtplib.SMTP") as mock_smtp_class:
        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 25
            mock_settings.smtp_username = None
            mock_settings.smtp_password = None
            mock_settings.smtp_use_tls = False
            
            mock_smtp = MagicMock()
            mock_smtp_class.return_value.__enter__.return_value = mock_smtp
            
            send_email(message)
            
            # Verify no TLS was started
            mock_smtp.starttls.assert_not_called()
            # Verify no authentication was performed
            mock_smtp.login.assert_not_called()
            mock_smtp.send_message.assert_called_once_with(message)


def test_send_confirmation_email() -> None:
    """Test the high-level confirmation email helper."""
    recipient = "test@example.com"
    confirmation_link = "https://example.com/confirm?token=xyz789"
    
    with patch("app.services.email.send_email") as mock_send:
        send_confirmation_email(recipient, confirmation_link)
        
        # Verify send_email was called with a message
        mock_send.assert_called_once()
        message = mock_send.call_args[0][0]
        assert isinstance(message, EmailMessage)
        assert message["To"] == recipient
        assert confirmation_link in str(message)

