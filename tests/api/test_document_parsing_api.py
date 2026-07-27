from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from tests.helpers import create_knowledge_space, upload_document

if TYPE_CHECKING:
    from tests.conftest import TenantScenario


@pytest.mark.api
class TestDocumentParsingApi:
    def test_parse_markdown_and_get_result(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        headers = tenant_scenario.admin_headers()
        ks_id = create_knowledge_space(api_client, headers)
        upload = upload_document(
            api_client,
            headers,
            ks_id,
            filename="guide.md",
            content=b"---\ntitle: Guide\n---\n\n# Intro\n\nParsed body.\n",
            content_type="text/markdown",
        )
        assert upload.status_code == 201
        document_id = upload.json()["id"]

        parse_response = api_client.post(f"/api/v1/documents/{document_id}/parse", headers=headers)
        assert parse_response.status_code == 200
        payload = parse_response.json()
        assert payload["status"] == "succeeded"
        assert payload["format"] == "markdown"
        assert "Parsed body" in payload["extracted_text"]
        assert payload["metadata"]["title"] == "Guide"
        assert payload["character_count"] > 0

        get_response = api_client.get(f"/api/v1/documents/{document_id}/parse", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["id"] == payload["id"]

    def test_parse_unsupported_format_returns_400(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        headers = tenant_scenario.admin_headers()
        ks_id = create_knowledge_space(api_client, headers)
        upload = upload_document(
            api_client,
            headers,
            ks_id,
            filename="data.bin",
            content=b"\x00\x01\x02",
            content_type="application/octet-stream",
        )
        assert upload.status_code == 201
        document_id = upload.json()["id"]

        response = api_client.post(f"/api/v1/documents/{document_id}/parse", headers=headers)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "UNSUPPORTED_DOCUMENT_FORMAT"

    def test_parse_corrupt_docx_persists_failed_status(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        headers = tenant_scenario.admin_headers()
        ks_id = create_knowledge_space(api_client, headers)
        upload = upload_document(
            api_client,
            headers,
            ks_id,
            filename="broken.docx",
            content=b"not-a-real-docx",
            content_type=(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
        )
        assert upload.status_code == 201
        document_id = upload.json()["id"]

        response = api_client.post(f"/api/v1/documents/{document_id}/parse", headers=headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "failed"
        assert payload["error_code"] == "DOCUMENT_PARSE_FAILED"
        assert payload["extracted_text"] is None

        stored = api_client.get(f"/api/v1/documents/{document_id}/parse", headers=headers)
        assert stored.status_code == 200
        assert stored.json()["status"] == "failed"

    def test_get_parse_without_prior_parse_returns_404(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        headers = tenant_scenario.admin_headers()
        ks_id = create_knowledge_space(api_client, headers)
        upload = upload_document(
            api_client,
            headers,
            ks_id,
            filename="guide.md",
            content=b"# Not parsed yet\n",
            content_type="text/markdown",
        )
        document_id = upload.json()["id"]
        response = api_client.get(f"/api/v1/documents/{document_id}/parse", headers=headers)
        assert response.status_code == 404

    def test_parse_requires_authentication(self, api_client: TestClient) -> None:
        response = api_client.post(f"/api/v1/documents/{uuid4()}/parse")
        assert response.status_code == 401
