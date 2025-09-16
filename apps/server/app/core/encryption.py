"""Encryption utilities for securing OAuth tokens at rest."""

from __future__ import annotations

import base64
import os
from cryptography.fernet import Fernet

from app.core.config import settings


def get_encryption_key() -> bytes:
    """Retrieve the encryption key from settings, decoding it from base64 if necessary."""
    # Try to get the key from environment variable first
    env_key = os.environ.get("ENCRYPTION_KEY")
    if env_key:
        return base64.urlsafe_b64decode(env_key)
    
    key = settings.encryption_key
    if isinstance(key, str):
        # If the key is a string, it should be base64 encoded
        return base64.urlsafe_b64decode(key)
    return key


# Initialize the Fernet cipher suite with our encryption key
_cipher_suite = Fernet(get_encryption_key())


def encrypt_token(token: str | None) -> str | None:
    """Encrypt a token using Fernet encryption."""
    if token is None:
        return None
    return _cipher_suite.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str | None) -> str | None:
    """Decrypt a token using Fernet encryption."""
    if encrypted_token is None:
        return None
    return _cipher_suite.decrypt(encrypted_token.encode()).decode()


__all__ = [
    "encrypt_token",
    "decrypt_token",
]
