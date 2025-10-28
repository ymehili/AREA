"""Tests for encryption utilities."""

import os
import pytest
import base64
from unittest.mock import patch

from app.core.encryption import (
    get_encryption_key,
    _get_cipher_suite,
    encrypt_token,
    decrypt_token
)
from app.core.config import settings


class TestEncryption:
    """Test encryption utilities."""

    def test_get_encryption_key_from_env(self):
        """Test getting encryption key from environment variable."""
        # Generate a proper 32-byte key for Fernet
        key_bytes = os.urandom(32)  # Use a proper random 32-byte key
        test_key = base64.urlsafe_b64encode(key_bytes).decode()
        
        with patch.dict(os.environ, {"ENCRYPTION_KEY": test_key}):
            result = get_encryption_key()
            
            assert result.decode() == test_key
            # Verify it's the correct length (32 bytes after decoding)
            decoded = base64.urlsafe_b64decode(result)
            assert len(decoded) == 32

    def test_get_encryption_key_from_settings(self):
        """Test getting encryption key from settings when not in environment."""
        # Generate a proper 32-byte key for Fernet
        key_bytes = os.urandom(32)  # Use a proper random 32-byte key
        test_key = base64.urlsafe_b64encode(key_bytes).decode()
        
        with patch.dict(os.environ, {}, clear=True):  # Clear environment
            with patch('app.core.encryption.settings') as mock_settings:
                mock_settings.encryption_key = test_key
                result = get_encryption_key()
                
                assert result.decode() == test_key
                decoded = base64.urlsafe_b64decode(result)
                assert len(decoded) == 32

    def test_get_encryption_key_not_configured(self):
        """Test getting encryption key when neither env nor settings are configured."""
        with patch.dict(os.environ, {}, clear=True):  # Clear environment
            with patch('app.core.encryption.settings') as mock_settings:
                mock_settings.encryption_key = None
                
                with pytest.raises(RuntimeError) as exc_info:
                    get_encryption_key()
                
                assert "ENCRYPTION_KEY environment variable or setting must be configured" in str(exc_info.value)

    def test_get_encryption_key_invalid_base64(self):
        """Test getting encryption key with invalid base64 string."""
        with patch.dict(os.environ, {"ENCRYPTION_KEY": "invalid_base64_key"}):
            with pytest.raises(ValueError) as exc_info:
                get_encryption_key()
            
            assert "ENCRYPTION_KEY must be a 32-byte url-safe base64 string" in str(exc_info.value)

    def test_get_encryption_key_wrong_length(self):
        """Test getting encryption key with wrong length (not 32 bytes after decode)."""
        # Create a key that's not 32 bytes after base64 decoding
        short_key = base64.urlsafe_b64encode(b"short").decode()
        
        with patch.dict(os.environ, {"ENCRYPTION_KEY": short_key}):
            with pytest.raises(ValueError) as exc_info:
                get_encryption_key()
            
            assert "ENCRYPTION_KEY must decode to exactly 32 bytes for Fernet" in str(exc_info.value)

    def test_encrypt_decrypt_token(self):
        """Test encrypting and decrypting a token."""
        test_token = "test_token_value"
        # Generate a proper 32-byte key for Fernet
        key_bytes = os.urandom(32)  # Use a proper random 32-byte key
        test_key = base64.urlsafe_b64encode(key_bytes).decode()
        
        with patch.dict(os.environ, {"ENCRYPTION_KEY": test_key}):
            # Clear the LRU cache to ensure it uses our test key
            _get_cipher_suite.cache_clear()
            
            # Encrypt the token
            encrypted = encrypt_token(test_token)
            assert encrypted is not None
            assert encrypted != test_token  # Should be different after encryption
            
            # Decrypt the token
            decrypted = decrypt_token(encrypted)
            assert decrypted == test_token

    def test_encrypt_decrypt_none_values(self):
        """Test encrypting and decrypting None values."""
        # Generate a proper 32-byte key for Fernet
        key_bytes = os.urandom(32)  # Use a proper random 32-byte key
        test_key = base64.urlsafe_b64encode(key_bytes).decode()
        
        with patch.dict(os.environ, {"ENCRYPTION_KEY": test_key}):
            # Clear the LRU cache to ensure it uses our test key
            _get_cipher_suite.cache_clear()
            
            # Encrypt None
            encrypted = encrypt_token(None)
            assert encrypted is None
            
            # Decrypt None
            decrypted = decrypt_token(None)
            assert decrypted is None

    def test_decrypt_invalid_token(self):
        """Test decrypting an invalid token."""
        # Generate a proper 32-byte key for Fernet
        key_bytes = os.urandom(32)  # Use a proper random 32-byte key
        test_key = base64.urlsafe_b64encode(key_bytes).decode()
        
        with patch.dict(os.environ, {"ENCRYPTION_KEY": test_key}):
            # Clear the LRU cache to ensure it uses our test key
            _get_cipher_suite.cache_clear()
            
            with pytest.raises(Exception):  # Could be cryptography.fernet.InvalidToken or similar
                decrypt_token("invalid_encrypted_token")

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption and decryption work as expected for multiple values."""
        # Generate a proper 32-byte key for Fernet
        key_bytes = os.urandom(32)  # Use a proper random 32-byte key
        test_key = base64.urlsafe_b64encode(key_bytes).decode()
        
        with patch.dict(os.environ, {"ENCRYPTION_KEY": test_key}):
            # Clear the LRU cache to ensure it uses our test key
            _get_cipher_suite.cache_clear()
            
            test_cases = [
                "simple_token",
                "token with spaces",
                "token_with_special_chars!@#$%",
                "token_with_12345_numbers",
                "",  # Empty string
            ]
            
            for token in test_cases:
                encrypted = encrypt_token(token)
                decrypted = decrypt_token(encrypted)
                assert decrypted == token