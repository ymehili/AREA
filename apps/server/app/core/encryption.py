"""Encryption utilities for securing OAuth tokens at rest."""

from __future__ import annotations

import base64
import os
from cryptography.fernet import Fernet

from app.core.config import settings


def get_encryption_key() -> bytes:
    """Resolve the configured Fernet key, validating it is usable."""

    key: str | bytes | None = os.environ.get("ENCRYPTION_KEY") or settings.encryption_key
    if not key:
        raise RuntimeError("ENCRYPTION_KEY environment variable or setting must be configured")

    key_bytes = key.encode("utf-8") if isinstance(key, str) else key

    try:
        decoded = base64.urlsafe_b64decode(key_bytes)
    except (ValueError, TypeError) as exc:
        raise ValueError("ENCRYPTION_KEY must be a 32-byte url-safe base64 string") from exc

    if len(decoded) != 32:
        raise ValueError("ENCRYPTION_KEY must decode to exactly 32 bytes for Fernet")

    return key_bytes


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
