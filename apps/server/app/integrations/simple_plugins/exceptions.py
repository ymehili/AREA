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
    "GitHubError",
    "GitHubAuthError",
    "GitHubAPIError",
    "GitHubConnectionError",
]
