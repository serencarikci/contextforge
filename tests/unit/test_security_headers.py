"""Unit tests for security response headers."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from contextforge.bootstrap.app_factory import create_app
from contextforge.shared.config.settings import Settings, clear_settings_cache


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("CONTEXTFORGE_APP_ENVIRONMENT", "test")
    clear_settings_cache()
    app = create_app(Settings())
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.unit
def test_security_headers_present(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "geolocation=()" in response.headers["Permissions-Policy"]
    assert "Strict-Transport-Security" not in response.headers


@pytest.mark.unit
def test_hsts_enabled_outside_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONTEXTFORGE_APP_ENVIRONMENT", "staging")
    monkeypatch.setenv("CONTEXTFORGE_API_DOCS_ENABLED", "false")
    clear_settings_cache()
    app = create_app(Settings())
    with TestClient(app) as client:
        response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert "max-age=" in response.headers["Strict-Transport-Security"]
