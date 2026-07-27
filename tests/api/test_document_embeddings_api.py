"""API tests for document embedding generation."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from tests.fakes import FakeVectorStore
from tests.helpers import create_knowledge_space

from contextforge.bootstrap.app_factory import create_app
from contextforge.shared.config.settings import Settings, clear_settings_cache

if TYPE_CHECKING:
    from tests.conftest import TenantScenario


def _upload_and_prepare(api_client: TestClient, headers: dict[str, str]) -> str:
    ks_id = create_knowledge_space(api_client, headers)
    turkish = "Bu belge Turkce ozel karakterler icerir: " + "\u011f\u00fc\u015f\u0131\u00f6\u00e7"
    body = "\n\n".join(
        [
            "# Genel Bakis",
            turkish,
            "# Overview",
            " ".join(f"token{i}" for i in range(80)),
        ]
    )
    upload = api_client.post(
        "/api/v1/documents",
        data={"knowledge_space_id": str(ks_id), "title": "Multilingual Doc"},
        files={"file": ("guide.md", body.encode("utf-8"), "text/markdown")},
        headers=headers,
    )
    assert upload.status_code == 201
    document_id = upload.json()["id"]
    parse_response = api_client.post(f"/api/v1/documents/{document_id}/parse", headers=headers)
    assert parse_response.status_code == 200
    chunk_response = api_client.post(f"/api/v1/documents/{document_id}/chunks", headers=headers)
    assert chunk_response.status_code == 200
    return str(document_id)


@pytest.mark.api
def test_embed_document_stores_vectors_and_updates_chunks(
    integration_settings: Settings, tenant_scenario: TenantScenario
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    fake_store = FakeVectorStore()
    app.state.vector_store = fake_store

    with TestClient(app) as api_client:
        headers = tenant_scenario.admin_headers()
        document_id = _upload_and_prepare(api_client, headers)

        response = api_client.post(
            f"/api/v1/documents/{document_id}/embeddings",
            headers=headers,
            params={"language": "tr"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["embedded_count"] >= 1
        assert payload["failed_count"] == 0
        assert payload["language"] == "tr"
        assert payload["dimensions"] == integration_settings.embedding.dimensions
        assert all(item["embedding_status"] == "embedded" for item in payload["items"])
        assert all(item["language"] == "tr" for item in payload["items"])
        assert fake_store.ensure_ready_calls >= 1
        assert len(fake_store.upserted) == payload["embedded_count"]
        assert fake_store.upserted[0].language == "tr"

        skipped = api_client.post(
            f"/api/v1/documents/{document_id}/embeddings",
            headers=headers,
            params={"language": "tr"},
        )
        assert skipped.status_code == 200
        assert skipped.json()["embedded_count"] == 0
        assert skipped.json()["skipped_count"] >= 1


@pytest.mark.api
def test_embed_without_chunks_returns_400(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    headers = tenant_scenario.admin_headers()
    ks_id = create_knowledge_space(api_client, headers)
    upload = api_client.post(
        "/api/v1/documents",
        data={"knowledge_space_id": str(ks_id), "title": "No Chunks"},
        files={"file": ("a.md", b"# Hi\n\nBody", "text/markdown")},
        headers=headers,
    )
    document_id = upload.json()["id"]
    api_client.post(f"/api/v1/documents/{document_id}/parse", headers=headers)
    response = api_client.post(f"/api/v1/documents/{document_id}/embeddings", headers=headers)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_RESOURCE_STATE"


@pytest.mark.api
def test_embed_requires_authentication(api_client: TestClient) -> None:
    response = api_client.post(f"/api/v1/documents/{uuid4()}/embeddings")
    assert response.status_code == 401
