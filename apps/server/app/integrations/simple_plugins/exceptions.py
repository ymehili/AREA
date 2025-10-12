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


class WeatherError(Exception):
    """Base exception for Weather operations."""

    pass


class WeatherAPIError(WeatherError):
    """Weather API request failed."""

    pass


class WeatherConfigError(WeatherError):
    """Weather configuration invalid or missing."""

    pass


__all__ = [
    "GmailError",
    "GmailAuthError",
    "GmailAPIError",
    "GmailConnectionError",
    "WeatherError",
    "WeatherAPIError",
    "WeatherConfigError",
]
