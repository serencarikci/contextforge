from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from tests.helpers import create_knowledge_space, upload_document

from contextforge.modules.documents.domain.entities.document import MAX_DOCUMENT_SIZE_BYTES

if TYPE_CHECKING:
    from tests.conftest import TenantScenario


@pytest.mark.api
class TestDocumentUploadAuthentication:
    def test_upload_without_identity_returns_401(self, api_client: TestClient) -> None:
        response = api_client.post(
            "/api/v1/documents",
            data={"knowledge_space_id": str(uuid4()), "title": "No Auth"},
            files={"file": ("f.txt", b"data", "text/plain")},
        )
        assert response.status_code == 401

    def test_download_without_identity_returns_401(self, api_client: TestClient) -> None:
        response = api_client.get(f"/api/v1/documents/{uuid4()}/download")
        assert response.status_code == 401


@pytest.mark.api
class TestDocumentLifecycle:
    def test_admin_can_upload_get_download_update_and_delete(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        headers = tenant_scenario.admin_headers()
        ks_id = create_knowledge_space(api_client, headers)

        upload_response = upload_document(api_client, headers, ks_id)
        assert upload_response.status_code == 201
        body = upload_response.json()
        assert body["title"] == "Test Doc"
        assert body["filename"] == "test.txt"
        assert body["knowledge_space_id"] == str(ks_id)
        assert body["status"] == "active"
        document_id = body["id"]

        get_response = api_client.get(f"/api/v1/documents/{document_id}", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["id"] == document_id

        download_response = api_client.get(
            f"/api/v1/documents/{document_id}/download", headers=headers
        )
        assert download_response.status_code == 200
        assert download_response.content == b"hello world"
        assert "attachment" in download_response.headers["content-disposition"]

        patch_response = api_client.patch(
            f"/api/v1/documents/{document_id}",
            json={"title": "Renamed Doc"},
            headers=headers,
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["title"] == "Renamed Doc"

        replace_response = api_client.put(
            f"/api/v1/documents/{document_id}/content",
            files={"file": ("new.txt", b"new content", "text/plain")},
            headers=headers,
        )
        assert replace_response.status_code == 200
        assert replace_response.json()["filename"] == "new.txt"

        redownload_response = api_client.get(
            f"/api/v1/documents/{document_id}/download", headers=headers
        )
        assert redownload_response.content == b"new content"

        delete_response = api_client.delete(f"/api/v1/documents/{document_id}", headers=headers)
        assert delete_response.status_code == 204

        get_after_delete = api_client.get(f"/api/v1/documents/{document_id}", headers=headers)
        assert get_after_delete.status_code == 404

    def test_list_documents_filters_by_knowledge_space(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        headers = tenant_scenario.admin_headers()
        ks_id = create_knowledge_space(api_client, headers)
        upload_document(api_client, headers, ks_id, title="Doc One")
        upload_document(api_client, headers, ks_id, title="Doc Two")

        response = api_client.get(
            "/api/v1/documents",
            params={"knowledge_space_id": str(ks_id)},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["pagination"]["total"] == 2
        titles = {item["title"] for item in body["items"]}
        assert titles == {"Doc One", "Doc Two"}

    def test_upload_rejects_file_over_max_size(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        headers = tenant_scenario.admin_headers()
        ks_id = create_knowledge_space(api_client, headers)
        oversized = b"x" * (MAX_DOCUMENT_SIZE_BYTES + 1)

        response = upload_document(api_client, headers, ks_id, content=oversized)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_RESOURCE_STATE"

    def test_upload_to_nonexistent_knowledge_space_returns_404(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        headers = tenant_scenario.admin_headers()
        response = upload_document(api_client, headers, str(uuid4()))
        assert response.status_code == 404


@pytest.mark.api
class TestDocumentAuthorization:
    def test_viewer_can_read_but_cannot_upload(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        admin_headers = tenant_scenario.admin_headers()
        ks_id = create_knowledge_space(api_client, admin_headers)
        upload_response = upload_document(api_client, admin_headers, ks_id)
        document_id = upload_response.json()["id"]

        viewer_headers = tenant_scenario.viewer_headers()
        get_response = api_client.get(f"/api/v1/documents/{document_id}", headers=viewer_headers)
        assert get_response.status_code == 200

        viewer_upload = upload_document(api_client, viewer_headers, ks_id, title="Viewer Doc")
        assert viewer_upload.status_code == 403
        assert viewer_upload.json()["error"]["code"] == "PERMISSION_DENIED"

    def test_viewer_cannot_update_metadata(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        admin_headers = tenant_scenario.admin_headers()
        ks_id = create_knowledge_space(api_client, admin_headers)
        upload_response = upload_document(api_client, admin_headers, ks_id)
        document_id = upload_response.json()["id"]

        viewer_headers = tenant_scenario.viewer_headers()
        response = api_client.patch(
            f"/api/v1/documents/{document_id}",
            json={"title": "Viewer Rename"},
            headers=viewer_headers,
        )
        assert response.status_code == 403

    def test_viewer_cannot_delete(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        admin_headers = tenant_scenario.admin_headers()
        ks_id = create_knowledge_space(api_client, admin_headers)
        upload_response = upload_document(api_client, admin_headers, ks_id)
        document_id = upload_response.json()["id"]

        viewer_headers = tenant_scenario.viewer_headers()
        response = api_client.delete(f"/api/v1/documents/{document_id}", headers=viewer_headers)
        assert response.status_code == 403


@pytest.mark.api
def test_cross_tenant_document_access_returns_404(
    api_client: TestClient,
    tenant_scenario: TenantScenario,
) -> None:
    admin_headers = tenant_scenario.admin_headers()
    ks_id = create_knowledge_space(api_client, admin_headers)
    upload_response = upload_document(api_client, admin_headers, ks_id)
    document_id = upload_response.json()["id"]
    other_org_headers = tenant_scenario.other_org_admin_headers()

    get_response = api_client.get(f"/api/v1/documents/{document_id}", headers=other_org_headers)
    assert get_response.status_code == 404
    assert get_response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

    download_response = api_client.get(
        f"/api/v1/documents/{document_id}/download", headers=other_org_headers
    )
    assert download_response.status_code == 404

    delete_response = api_client.delete(
        f"/api/v1/documents/{document_id}", headers=other_org_headers
    )
    assert delete_response.status_code == 404
