"""API tests for document endpoints: authentication, RBAC, and tenant isolation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.documents.domain.entities.document import MAX_DOCUMENT_SIZE_BYTES
from contextforge.modules.identity_access.application.services.user_service import UserService
from contextforge.modules.organizations.application.services.organization_service import (
    OrganizationService,
)

if TYPE_CHECKING:
    from tests.conftest import TenantScenario

    from contextforge.infrastructure.database.session import DatabaseManager

USER_ID_HEADER = "X-ContextForge-User-ID"
ORGANIZATION_ID_HEADER = "X-ContextForge-Organization-ID"


def _create_knowledge_space(api_client: TestClient, headers: dict[str, str]) -> str:
    response = api_client.post(
        "/api/v1/knowledge-spaces",
        json={"name": "Docs KS", "slug": f"docs-ks-{uuid4().hex[:10]}"},
        headers=headers,
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def _upload_document(
    api_client: TestClient,
    headers: dict[str, str],
    knowledge_space_id: str,
    *,
    title: str = "Test Doc",
    filename: str = "test.txt",
    content: bytes = b"hello world",
    content_type: str = "text/plain",
) -> Any:
    return api_client.post(
        "/api/v1/documents",
        data={"knowledge_space_id": knowledge_space_id, "title": title},
        files={"file": (filename, content, content_type)},
        headers=headers,
    )


@pytest_asyncio.fixture
async def other_org_admin_headers(db_manager: DatabaseManager) -> dict[str, str]:
    """Headers for an admin in a completely independent organization.

    Used to assert that document access is scoped by ``organization_id`` and
    not just by "the caller has *some* valid identity".
    """
    suffix = uuid4().hex[:12]
    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    admin = await UserService().create(
        uow, email=f"doc-other-admin-{suffix}@example.com", display_name="Other Org Admin"
    )
    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    organization = await OrganizationService().create(
        uow,
        name=f"Other Doc Org {suffix}",
        slug=f"other-doc-org-{suffix}",
        creator_user_id=admin.id,
    )
    return {
        USER_ID_HEADER: str(admin.id),
        ORGANIZATION_ID_HEADER: str(organization.id),
    }


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
        ks_id = _create_knowledge_space(api_client, headers)

        upload_response = _upload_document(api_client, headers, ks_id)
        assert upload_response.status_code == 201
        body = upload_response.json()
        assert body["title"] == "Test Doc"
        assert body["filename"] == "test.txt"
        assert body["knowledge_space_id"] == ks_id
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
        ks_id = _create_knowledge_space(api_client, headers)
        _upload_document(api_client, headers, ks_id, title="Doc One")
        _upload_document(api_client, headers, ks_id, title="Doc Two")

        response = api_client.get(
            "/api/v1/documents",
            params={"knowledge_space_id": ks_id},
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
        ks_id = _create_knowledge_space(api_client, headers)
        oversized = b"x" * (MAX_DOCUMENT_SIZE_BYTES + 1)

        response = _upload_document(api_client, headers, ks_id, content=oversized)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_RESOURCE_STATE"

    def test_upload_to_nonexistent_knowledge_space_returns_404(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        headers = tenant_scenario.admin_headers()
        response = _upload_document(api_client, headers, str(uuid4()))
        assert response.status_code == 404


@pytest.mark.api
class TestDocumentAuthorization:
    def test_viewer_can_read_but_cannot_upload(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        admin_headers = tenant_scenario.admin_headers()
        ks_id = _create_knowledge_space(api_client, admin_headers)
        upload_response = _upload_document(api_client, admin_headers, ks_id)
        document_id = upload_response.json()["id"]

        viewer_headers = tenant_scenario.viewer_headers()
        get_response = api_client.get(f"/api/v1/documents/{document_id}", headers=viewer_headers)
        assert get_response.status_code == 200

        viewer_upload = _upload_document(api_client, viewer_headers, ks_id, title="Viewer Doc")
        assert viewer_upload.status_code == 403
        assert viewer_upload.json()["error"]["code"] == "PERMISSION_DENIED"

    def test_viewer_cannot_update_metadata(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        admin_headers = tenant_scenario.admin_headers()
        ks_id = _create_knowledge_space(api_client, admin_headers)
        upload_response = _upload_document(api_client, admin_headers, ks_id)
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
        ks_id = _create_knowledge_space(api_client, admin_headers)
        upload_response = _upload_document(api_client, admin_headers, ks_id)
        document_id = upload_response.json()["id"]

        viewer_headers = tenant_scenario.viewer_headers()
        response = api_client.delete(f"/api/v1/documents/{document_id}", headers=viewer_headers)
        assert response.status_code == 403


@pytest.mark.api
def test_cross_tenant_document_access_returns_404(
    api_client: TestClient,
    tenant_scenario: TenantScenario,
    other_org_admin_headers: dict[str, str],
) -> None:
    """A document that belongs to one organization is invisible to another."""
    admin_headers = tenant_scenario.admin_headers()
    ks_id = _create_knowledge_space(api_client, admin_headers)
    upload_response = _upload_document(api_client, admin_headers, ks_id)
    document_id = upload_response.json()["id"]

    get_response = api_client.get(
        f"/api/v1/documents/{document_id}", headers=other_org_admin_headers
    )
    assert get_response.status_code == 404
    assert get_response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

    download_response = api_client.get(
        f"/api/v1/documents/{document_id}/download", headers=other_org_admin_headers
    )
    assert download_response.status_code == 404

    delete_response = api_client.delete(
        f"/api/v1/documents/{document_id}", headers=other_org_admin_headers
    )
    assert delete_response.status_code == 404
