from app.core.config import Settings


def test_settings_use_database_url_alias(monkeypatch):
    custom_url = "postgresql+psycopg://user:pass@host:5432/db"
    monkeypatch.setenv("DATABASE_URL", custom_url)

    settings = Settings()
    assert settings.database_url == custom_url


def test_settings_default_database_url_is_postgres(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = Settings()
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_email_settings_use_aliases(monkeypatch):
    monkeypatch.setenv("EMAIL_SENDER", "noreply@example.com")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "2525")
    monkeypatch.setenv("SMTP_USE_TLS", "true")

    settings = Settings()
    assert settings.email_sender == "noreply@example.com"
    assert settings.smtp_host == "smtp.example.com"
    assert settings.smtp_port == 2525
    assert settings.smtp_use_tls is True


def test_confirmation_urls_have_defaults(monkeypatch):
    monkeypatch.delenv("EMAIL_CONFIRMATION_BASE_URL", raising=False)
    monkeypatch.delenv("EMAIL_CONFIRMATION_SUCCESS_REDIRECT_URL", raising=False)
    monkeypatch.delenv("EMAIL_CONFIRMATION_FAILURE_REDIRECT_URL", raising=False)

    settings = Settings()
    assert settings.email_confirmation_base_url.endswith("/api/v1/auth/confirm")
    assert settings.email_confirmation_success_redirect_url.endswith("/confirm/success")
    assert settings.email_confirmation_failure_redirect_url.endswith("/confirm/error")
