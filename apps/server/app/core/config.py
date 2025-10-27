"""Application configuration using Pydantic settings."""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings sourced from environment variables and .env files."""

    database_url: str = Field(
        default="postgresql+psycopg://area:area@localhost:5432/area",
        alias="DATABASE_URL",
    )

    secret_key: str = Field(
        default="dev-secret-key",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        alias="JWT_ALGORITHM",
    )
    access_token_expire_minutes: int = Field(
        default=30,
        alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    
    encryption_key: str = Field(
        default="",
        alias="ENCRYPTION_KEY",
    )

    email_sender: str = Field(
        default="no-reply@action-reaction.local",
        alias="EMAIL_SENDER",
    )
    smtp_host: str = Field(
        default="localhost",
        alias="SMTP_HOST",
    )
    smtp_port: int = Field(
        default=1025,
        alias="SMTP_PORT",
    )
    smtp_username: Optional[str] = Field(
        default=None,
        alias="SMTP_USERNAME",
    )
    smtp_password: Optional[str] = Field(
        default=None,
        alias="SMTP_PASSWORD",
    )
    smtp_use_tls: bool = Field(
        default=False,
        alias="SMTP_USE_TLS",
    )
    email_confirmation_token_expiry_minutes: int = Field(
        default=60 * 24,
        alias="EMAIL_CONFIRMATION_TOKEN_EXPIRY_MINUTES",
    )
    email_confirmation_base_url: str = Field(
        default="http://localhost:8080/api/v1/auth/confirm",
        alias="EMAIL_CONFIRMATION_BASE_URL",
    )
    email_confirmation_success_redirect_url: str = Field(
        default="http://localhost:3000/confirm/success",
        alias="EMAIL_CONFIRMATION_SUCCESS_REDIRECT_URL",
    )
    email_confirmation_failure_redirect_url: str = Field(
        default="http://localhost:3000/confirm/error",
        alias="EMAIL_CONFIRMATION_FAILURE_REDIRECT_URL",
    )

    # OAuth settings
    google_client_id: str = Field(
        default="",
        alias="GOOGLE_CLIENT_ID",
    )
    google_client_secret: str = Field(
        default="",
        alias="GOOGLE_CLIENT_SECRET",
    )
    oauth_redirect_base_url: str = Field(
        default="http://localhost:8080/api/v1/oauth",
        alias="OAUTH_REDIRECT_BASE_URL",
    )
    frontend_redirect_url_web: str = Field(
        default="http://localhost:3000",
        alias="FRONTEND_REDIRECT_URL_WEB",
    )
    frontend_redirect_url_mobile: str = Field(
        default="areamobile://oauth/callback",
        alias="FRONTEND_REDIRECT_URL_MOBILE"
    )

    # GitHub OAuth Configuration
    github_client_id: str = Field(
        default="",
        alias="GITHUB_CLIENT_ID",
    )
    github_client_secret: str = Field(
        default="",
        alias="GITHUB_CLIENT_SECRET",
    )

    # Gmail Scheduler Configuration
    gmail_poll_interval_seconds: int = Field(
        default=15,
        alias="GMAIL_POLL_INTERVAL_SECONDS",
        description="Gmail polling interval in seconds (default: 15). Lower values increase API usage.",
    )

    # Google Calendar Scheduler Configuration
    calendar_poll_interval_seconds: int = Field(
        default=15,
        alias="CALENDAR_POLL_INTERVAL_SECONDS",
        description="Google Calendar polling interval in seconds (default: 15). Lower values increase API usage.",
    )

    # Google Drive Scheduler Configuration
    google_drive_poll_interval_seconds: int = Field(
        default=60,
        alias="GOOGLE_DRIVE_POLL_INTERVAL_SECONDS",
        description="Google Drive polling interval in seconds (default: 60). Lower values increase API usage.",
    )

    # OpenWeatherMap API Configuration
    openweathermap_api_key: str = Field(
        default="",
        alias="OPENWEATHERMAP_API_KEY",
        description="API key for OpenWeatherMap API (get free key at https://openweathermap.org/api)",
    )

    # Microsoft Graph API / Outlook Configuration
    microsoft_client_id: str = Field(
        default="",
        alias="MICROSOFT_CLIENT_ID",
    )
    microsoft_client_secret: str = Field(
        default="",
        alias="MICROSOFT_CLIENT_SECRET",
    )
    outlook_poll_interval_seconds: int = Field(
        default=15,
        alias="OUTLOOK_POLL_INTERVAL_SECONDS",
        description="Outlook polling interval in seconds (default: 15).",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()

__all__ = ["Settings", "settings"]
