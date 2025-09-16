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
