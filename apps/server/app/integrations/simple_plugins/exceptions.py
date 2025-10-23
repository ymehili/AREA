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


class OpenAIError(Exception):
    """Base exception for OpenAI operations."""

    pass


class OpenAIAuthError(OpenAIError):
    """OpenAI authentication/authorization failed."""

    pass


class OpenAIAPIError(OpenAIError):
    """OpenAI API request failed."""

    pass


class OpenAIConnectionError(OpenAIError):
    """OpenAI service connection not found or invalid."""

    pass


class OpenAIConfigError(OpenAIError):
    """OpenAI configuration invalid or missing."""

    pass


class CalendarError(Exception):
    """Base exception for Calendar operations."""

    pass


class CalendarAuthError(CalendarError):
    """Calendar authentication/authorization failed."""

    pass


class CalendarAPIError(CalendarError):
    """Calendar API request failed."""

    pass


class CalendarConnectionError(CalendarError):
    """Calendar service connection not found or invalid."""

    pass


class GitHubError(Exception):
    """Base exception for GitHub operations."""

    pass


class GitHubAuthError(GitHubError):
    """GitHub authentication/authorization failed."""

    pass


class GitHubAPIError(GitHubError):
    """GitHub API request failed."""

    pass


class GitHubConnectionError(GitHubError):
    """GitHub service connection not found or invalid."""

    pass


class RSSError(Exception):
    """Base exception for RSS operations."""

    pass


class RSSFeedError(RSSError):
    """RSS feed parsing or processing failed."""

    pass


class RSSConnectionError(RSSError):
    """RSS feed connection or fetch failed."""

    pass


__all__ = [
    "GmailError",
    "GmailAuthError",
    "GmailAPIError",
    "GmailConnectionError",
    "WeatherError",
    "WeatherAPIError",
    "WeatherConfigError",
    "OpenAIError",
    "OpenAIAuthError",
    "OpenAIAPIError",
    "OpenAIConnectionError",
    "OpenAIConfigError",
    "CalendarError",
    "CalendarAuthError",
    "CalendarAPIError",
    "CalendarConnectionError",
    "GitHubError",
    "GitHubAuthError",
    "GitHubAPIError",
    "GitHubConnectionError",
    "RSSError",
    "RSSFeedError",
    "RSSConnectionError",
]
