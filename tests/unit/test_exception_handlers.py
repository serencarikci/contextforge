"""Unit tests for exception response formatting."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from contextforge.bootstrap.app_factory import create_app
from contextforge.domain.exceptions.base import DomainError
from contextforge.shared.config.settings import Settings, clear_settings_cache


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("CONTEXTFORGE_APP__ENVIRONMENT", "test")
    clear_settings_cache()
    settings = Settings()
    app = create_app(settings)

    @app.get("/api/v1/_test/domain-error")
    async def domain_error() -> None:
        raise DomainError("Invalid state.", code="INVALID_STATE")

    @app.get("/api/v1/_test/boom")
    async def boom() -> None:
        raise RuntimeError("secret internal details")

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.mark.unit
def test_domain_error_response_format(client: TestClient) -> None:
    response = client.get("/api/v1/_test/domain-error")
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "INVALID_STATE"
    assert body["error"]["message"] == "Invalid state."
    assert "correlation_id" in body["error"]


@pytest.mark.unit
def test_unhandled_error_hides_internal_details(client: TestClient) -> None:
    response = client.get("/api/v1/_test/boom")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert body["error"]["message"] == "An unexpected error occurred."
    assert "secret internal details" not in response.text


@pytest.mark.unit
def test_validation_error_response(client: TestClient) -> None:
    # Hit an endpoint with an invalid query shape via OpenAPI-validated path if present.
    # Use a non-existent method to exercise HTTP exception formatting.
    response = client.request("TRACE", "/api/v1/health/live")
    assert response.status_code in {405, 400, 404, 422}
    assert "error" in response.json()
