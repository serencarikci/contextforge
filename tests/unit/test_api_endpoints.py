"""Unit tests for system info and liveness endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from contextforge.bootstrap.app_factory import create_app
from contextforge.shared.config.settings import Settings, clear_settings_cache


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("CONTEXTFORGE_APP__ENVIRONMENT", "test")
    clear_settings_cache()
    app = create_app(Settings())
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.unit
def test_liveness(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "status": "ok",
        "service": "contextforge-api",
        "version": "0.1.0",
    }
    assert "X-Correlation-ID" in response.headers


@pytest.mark.unit
def test_correlation_id_passthrough(client: TestClient) -> None:
    cid = "550e8400-e29b-41d4-a716-446655440000"
    response = client.get("/api/v1/health/live", headers={"X-Correlation-ID": cid})
    assert response.headers["X-Correlation-ID"] == cid


@pytest.mark.unit
def test_system_info_capabilities_false(client: TestClient) -> None:
    response = client.get("/api/v1/system/info")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "ContextForge API"
    assert body["version"] == "0.1.0"
    assert body["environment"] == "test"
    assert body["capabilities"] == {
        "identity_context": True,
        "multi_tenancy": True,
        "rbac": True,
        "customers": True,
        "projects": True,
        "knowledge_spaces": True,
        "audit_log": True,
        "document_ingestion": False,
        "rag": False,
        "chat": False,
        "multilingual_answers": False,
    }
    assert body["authentication"] == "development_only"
