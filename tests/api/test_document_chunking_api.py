"""API tests for document chunking endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from tests.conftest import TenantScenario


def _create_knowledge_space(api_client: TestClient, headers: dict[str, str]) -> str:
    response = api_client.post(
        "/api/v1/knowledge-spaces",
        json={"name": "Chunk KS", "slug": f"chunk-ks-{uuid4().hex[:10]}"},
        headers=headers,
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def _upload_markdown(
    api_client: TestClient,
    headers: dict[str, str],
    knowledge_space_id: str,
) -> Any:
    body = "\n\n".join(
        [
            "# Overview",
            " ".join(f"alpha{i}" for i in range(120)),
            "# Architecture",
            " ".join(f"beta{i}" for i in range(120)),
            "## Persistence",
            " ".join(f"gamma{i}" for i in range(100)),
        ]
    )
    return api_client.post(
        "/api/v1/documents",
        data={"knowledge_space_id": knowledge_space_id, "title": "Chunk Doc"},
        files={"file": ("guide.md", body.encode("utf-8"), "text/markdown")},
        headers=headers,
    )


@pytest.mark.api
class TestDocumentChunkingApi:
    def test_chunk_after_parse_and_list(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        headers = tenant_scenario.admin_headers()
        ks_id = _create_knowledge_space(api_client, headers)
        upload = _upload_markdown(api_client, headers, ks_id)
        assert upload.status_code == 201
        document_id = upload.json()["id"]

        parse_response = api_client.post(f"/api/v1/documents/{document_id}/parse", headers=headers)
        assert parse_response.status_code == 200
        assert parse_response.json()["status"] == "succeeded"

        chunk_response = api_client.post(f"/api/v1/documents/{document_id}/chunks", headers=headers)
        assert chunk_response.status_code == 200
        payload = chunk_response.json()
        assert payload["total"] >= 1
        assert len(payload["items"]) == payload["total"]
        first = payload["items"][0]
        assert first["chunk_index"] == 0
        assert first["embedding_status"] == "pending"
        assert first["token_count"] > 0
        assert first["content_hash"]
        assert first["metadata"]["source_format"] == "markdown"
        assert first["metadata"]["document_title"] == "Chunk Doc"
        assert first["parse_result_id"] == parse_response.json()["id"]

        listed = api_client.get(f"/api/v1/documents/{document_id}/chunks", headers=headers)
        assert listed.status_code == 200
        assert listed.json()["total"] == payload["total"]

    def test_chunk_without_parse_returns_400(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        headers = tenant_scenario.admin_headers()
        ks_id = _create_knowledge_space(api_client, headers)
        upload = _upload_markdown(api_client, headers, ks_id)
        document_id = upload.json()["id"]

        response = api_client.post(f"/api/v1/documents/{document_id}/chunks", headers=headers)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_RESOURCE_STATE"

    def test_chunk_requires_authentication(self, api_client: TestClient) -> None:
        response = api_client.post(f"/api/v1/documents/{uuid4()}/chunks")
        assert response.status_code == 401
