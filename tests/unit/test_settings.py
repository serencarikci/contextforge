from __future__ import annotations

import pytest

from contextforge.shared.config.settings import (
    Environment,
    Settings,
    clear_settings_cache,
)


@pytest.mark.unit
def test_settings_load_nested_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONTEXTFORGE_APP_ENVIRONMENT", "development")
    monkeypatch.setenv("CONTEXTFORGE_POSTGRES_HOST", "db.internal")
    monkeypatch.setenv("CONTEXTFORGE_POSTGRES_PORT", "5433")
    monkeypatch.setenv("CONTEXTFORGE_REDIS_URL", "redis://cache:6379/1")
    monkeypatch.setenv("CONTEXTFORGE_QDRANT_URL", "http://qdrant:6333")
    monkeypatch.setenv("CONTEXTFORGE_MINIO_ENDPOINT", "minio:9000")
    monkeypatch.setenv("CONTEXTFORGE_LOGGING_LEVEL", "DEBUG")
    clear_settings_cache()

    settings = Settings()

    assert settings.app.environment == Environment.DEVELOPMENT
    assert settings.postgres.host == "db.internal"
    assert settings.postgres.port == 5433
    assert settings.redis.url == "redis://cache:6379/1"
    assert settings.qdrant.url == "http://qdrant:6333"
    assert settings.minio.endpoint == "minio:9000"
    assert settings.logging.level == "DEBUG"


@pytest.mark.unit
def test_production_disables_docs_and_forces_json_logging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONTEXTFORGE_APP_ENVIRONMENT", "production")
    monkeypatch.setenv("CONTEXTFORGE_API_DOCS_ENABLED", "true")
    monkeypatch.setenv("CONTEXTFORGE_LOGGING_FORMAT", "console")
    clear_settings_cache()

    settings = Settings()

    assert settings.api.docs_enabled is False
    assert settings.logging.format == "json"


@pytest.mark.unit
def test_postgres_async_dsn_contains_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONTEXTFORGE_POSTGRES_USER", "cf_user")
    monkeypatch.setenv("CONTEXTFORGE_POSTGRES_PASSWORD", "secret")
    monkeypatch.setenv("CONTEXTFORGE_POSTGRES_HOST", "localhost")
    monkeypatch.setenv("CONTEXTFORGE_POSTGRES_DATABASE", "contextforge")
    clear_settings_cache()

    settings = Settings()
    assert "cf_user:secret@localhost:5432/contextforge" in settings.postgres.async_dsn
