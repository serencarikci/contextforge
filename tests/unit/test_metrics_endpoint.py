from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from contextforge.bootstrap.app_factory import create_app
from contextforge.shared.config.settings import Settings, clear_settings_cache


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("CONTEXTFORGE_APP_ENVIRONMENT", "test")
    monkeypatch.setenv("CONTEXTFORGE_OBSERVABILITY_METRICS_ENABLED", "true")
    clear_settings_cache()
    app = create_app(Settings())
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.unit
def test_metrics_endpoint_exposes_prometheus_text(client: TestClient) -> None:
    client.get("/api/v1/health/live")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    assert "contextforge_http_requests_total" in body
    assert "contextforge_http_request_duration_seconds" in body
