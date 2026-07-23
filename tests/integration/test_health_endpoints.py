"""Integration tests for health endpoints against real infrastructure."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_live_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.integration
def test_ready_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    for name in ("postgresql", "redis", "qdrant", "minio"):
        assert body["checks"][name]["status"] == "up"
        assert body["checks"][name]["latency_ms"] >= 0
    assert body["total_latency_ms"] >= 0


@pytest.mark.integration
def test_system_info_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/system/info")
    assert response.status_code == 200
    body = response.json()
    assert body["capabilities"]["rag"] is False
    assert body["capabilities"]["chat"] is False
