"""Exceptions for simple plugin integrations."""

from __future__ import annotations


class GmailError(Exception):
    """Base exception for Gmail operations."""

    pass


class GmailAuthError(GmailError):
    """Gmail authentication/authorization failed."""

    pass


class GmailAPIError(GmailError):
    """Gmail API request failed."""

    pass


class GmailConnectionError(GmailError):
    """Gmail service connection not found or invalid."""

    pass


__all__ = ["GmailError", "GmailAuthError", "GmailAPIError", "GmailConnectionError"]
