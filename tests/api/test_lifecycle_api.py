"""API tests exercising broader CRUD lifecycles as an organization admin.

These complement the narrower authorization-focused tests
(`test_customers_api.py`, `test_tenant_isolation_api.py`,
`tests/security/`) by walking each resource type through its normal
create/read/update/list/terminal-state lifecycle via real HTTP requests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from tests.conftest import TenantScenario


@pytest.mark.api
class TestOrganizationLifecycle:
    def test_list_organizations_includes_own_organization(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        response = api_client.get("/api/v1/organizations", headers=tenant_scenario.admin_headers())
        assert response.status_code == 200
        ids = {item["id"] for item in response.json()["items"]}
        assert str(tenant_scenario.organization_id) in ids

    def test_update_organization_name(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        response = api_client.patch(
            f"/api/v1/organizations/{tenant_scenario.organization_id}",
            json={"name": "Renamed Tenant Org"},
            headers=tenant_scenario.admin_headers(),
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Renamed Tenant Org"

    def test_viewer_cannot_update_organization(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        response = api_client.patch(
            f"/api/v1/organizations/{tenant_scenario.organization_id}",
            json={"name": "Viewer Renamed Org"},
            headers=tenant_scenario.viewer_headers(),
        )
        assert response.status_code == 403

    def test_suspend_and_archive_organization(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        suspend_response = api_client.post(
            f"/api/v1/organizations/{tenant_scenario.organization_id}/suspend",
            headers=tenant_scenario.admin_headers(),
        )
        assert suspend_response.status_code == 200
        assert suspend_response.json()["status"] == "suspended"

        archive_response = api_client.post(
            f"/api/v1/organizations/{tenant_scenario.organization_id}/archive",
            headers=tenant_scenario.admin_headers(),
        )
        assert archive_response.status_code == 200
        assert archive_response.json()["status"] == "archived"


@pytest.mark.api
class TestProjectLifecycle:
    def test_create_get_list_update_archive_project(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        create_response = api_client.post(
            "/api/v1/projects",
            json={
                "name": "Lifecycle Project",
                "key": f"P{uuid4().hex[:6].upper()}",
                "customer_id": str(tenant_scenario.customer_id),
            },
            headers=tenant_scenario.admin_headers(),
        )
        assert create_response.status_code == 201
        project = create_response.json()
        assert project["customer_id"] == str(tenant_scenario.customer_id)
        assert project["status"] == "active"

        get_response = api_client.get(
            f"/api/v1/projects/{project['id']}", headers=tenant_scenario.admin_headers()
        )
        assert get_response.status_code == 200

        list_response = api_client.get("/api/v1/projects", headers=tenant_scenario.admin_headers())
        assert list_response.status_code == 200
        assert project["id"] in {item["id"] for item in list_response.json()["items"]}

        update_response = api_client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"description": "Updated description"},
            headers=tenant_scenario.admin_headers(),
        )
        assert update_response.status_code == 200
        assert update_response.json()["description"] == "Updated description"

        archive_response = api_client.post(
            f"/api/v1/projects/{project['id']}/archive",
            headers=tenant_scenario.admin_headers(),
        )
        assert archive_response.status_code == 200
        assert archive_response.json()["status"] == "archived"

    def test_viewer_cannot_create_project(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        response = api_client.post(
            "/api/v1/projects",
            json={"name": "Viewer Project", "key": "VIEWPRJ"},
            headers=tenant_scenario.viewer_headers(),
        )
        assert response.status_code == 403


@pytest.mark.api
class TestMembershipLifecycle:
    def test_add_list_get_suspend_remove_membership(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        new_user_response = api_client.post(
            "/api/v1/users",
            json={
                "email": f"new-member-{uuid4().hex[:10]}@example.com",
                "display_name": "New Member",
            },
            headers=tenant_scenario.admin_headers(),
        )
        assert new_user_response.status_code == 201
        new_user_id = new_user_response.json()["id"]

        add_response = api_client.post(
            "/api/v1/memberships",
            json={"user_id": new_user_id},
            headers=tenant_scenario.admin_headers(),
        )
        assert add_response.status_code == 201
        membership = add_response.json()
        assert membership["user_id"] == new_user_id
        assert membership["status"] == "active"

        list_response = api_client.get(
            "/api/v1/memberships", headers=tenant_scenario.admin_headers()
        )
        assert list_response.status_code == 200
        assert membership["id"] in {item["id"] for item in list_response.json()["items"]}

        get_response = api_client.get(
            f"/api/v1/memberships/{membership['id']}", headers=tenant_scenario.admin_headers()
        )
        assert get_response.status_code == 200

        suspend_response = api_client.post(
            f"/api/v1/memberships/{membership['id']}/suspend",
            headers=tenant_scenario.admin_headers(),
        )
        assert suspend_response.status_code == 200
        assert suspend_response.json()["status"] == "suspended"

        remove_response = api_client.delete(
            f"/api/v1/memberships/{membership['id']}", headers=tenant_scenario.admin_headers()
        )
        assert remove_response.status_code == 200
        assert remove_response.json()["status"] == "removed"

    def test_duplicate_membership_is_rejected(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        response = api_client.post(
            "/api/v1/memberships",
            json={"user_id": str(tenant_scenario.viewer_user_id)},
            headers=tenant_scenario.admin_headers(),
        )
        assert response.status_code == 409


@pytest.mark.api
class TestRoleLifecycle:
    def test_list_roles_includes_system_roles(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        response = api_client.get("/api/v1/roles", headers=tenant_scenario.admin_headers())
        assert response.status_code == 200
        codes = {item["code"] for item in response.json()}
        assert "organization_admin" in codes
        assert "viewer" in codes

    def test_create_update_org_role(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        create_response = api_client.post(
            "/api/v1/roles",
            json={"code": "custom_reviewer", "name": "Custom Reviewer"},
            headers=tenant_scenario.admin_headers(),
        )
        assert create_response.status_code == 201
        role = create_response.json()
        assert role["is_system"] is False

        update_response = api_client.patch(
            f"/api/v1/roles/{role['id']}",
            json={"name": "Renamed Reviewer"},
            headers=tenant_scenario.admin_headers(),
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Renamed Reviewer"

    def test_list_role_assignments_and_revoke(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        list_response = api_client.get(
            "/api/v1/roles/assignments", headers=tenant_scenario.admin_headers()
        )
        assert list_response.status_code == 200
        assignments = list_response.json()["items"]
        viewer_assignment = next(
            item
            for item in assignments
            if item["membership_id"] == str(tenant_scenario.viewer_membership_id)
        )

        revoke_response = api_client.delete(
            f"/api/v1/roles/assignments/{viewer_assignment['id']}",
            headers=tenant_scenario.admin_headers(),
        )
        assert revoke_response.status_code == 204

        forbidden_response = api_client.get(
            f"/api/v1/customers/{tenant_scenario.customer_id}",
            headers=tenant_scenario.viewer_headers(),
        )
        assert forbidden_response.status_code == 403


@pytest.mark.api
class TestUserLifecycle:
    def test_create_get_update_suspend_archive_user(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        create_response = api_client.post(
            "/api/v1/users",
            json={
                "email": f"lifecycle-user-{uuid4().hex[:10]}@example.com",
                "display_name": "Lifecycle User",
            },
            headers=tenant_scenario.admin_headers(),
        )
        assert create_response.status_code == 201
        user = create_response.json()

        api_client.post(
            "/api/v1/memberships",
            json={"user_id": user["id"]},
            headers=tenant_scenario.admin_headers(),
        )

        get_response = api_client.get(
            f"/api/v1/users/{user['id']}", headers=tenant_scenario.admin_headers()
        )
        assert get_response.status_code == 200

        update_response = api_client.patch(
            f"/api/v1/users/{user['id']}",
            json={"display_name": "Renamed Lifecycle User"},
            headers=tenant_scenario.admin_headers(),
        )
        assert update_response.status_code == 200
        assert update_response.json()["display_name"] == "Renamed Lifecycle User"

        suspend_response = api_client.post(
            f"/api/v1/users/{user['id']}/suspend", headers=tenant_scenario.admin_headers()
        )
        assert suspend_response.status_code == 200
        assert suspend_response.json()["status"] == "suspended"

        archive_response = api_client.post(
            f"/api/v1/users/{user['id']}/archive", headers=tenant_scenario.admin_headers()
        )
        assert archive_response.status_code == 200
        assert archive_response.json()["status"] == "archived"

    def test_user_can_read_and_update_their_own_profile_without_manage_permission(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        get_response = api_client.get(
            f"/api/v1/users/{tenant_scenario.viewer_user_id}",
            headers=tenant_scenario.viewer_headers(),
        )
        assert get_response.status_code == 200

        update_response = api_client.patch(
            f"/api/v1/users/{tenant_scenario.viewer_user_id}",
            json={"display_name": "Self Updated Viewer"},
            headers=tenant_scenario.viewer_headers(),
        )
        assert update_response.status_code == 200


@pytest.mark.api
class TestAuditLifecycle:
    def test_list_audit_events_includes_customer_creation(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        response = api_client.get(
            "/api/v1/audit",
            params={"resource_type": "customer", "action": "customer.created"},
            headers=tenant_scenario.admin_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["pagination"]["total"] >= 1
        assert all(item["resource_type"] == "customer" for item in body["items"])

    def test_viewer_without_audit_read_permission_is_denied(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        response = api_client.get("/api/v1/audit", headers=tenant_scenario.viewer_headers())
        assert response.status_code == 403


@pytest.mark.api
class TestKnowledgeSpaceLifecycle:
    def test_create_get_update_archive_org_visible_space(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:
        create_response = api_client.post(
            "/api/v1/knowledge-spaces",
            json={"name": "Handbook", "slug": f"handbook-{uuid4().hex[:10]}"},
            headers=tenant_scenario.admin_headers(),
        )
        assert create_response.status_code == 201
        space = create_response.json()
        assert space["visibility"] == "organization"

        viewer_get = api_client.get(
            f"/api/v1/knowledge-spaces/{space['id']}", headers=tenant_scenario.viewer_headers()
        )
        assert viewer_get.status_code == 200

        update_response = api_client.patch(
            f"/api/v1/knowledge-spaces/{space['id']}",
            json={"description": "Updated"},
            headers=tenant_scenario.admin_headers(),
        )
        assert update_response.status_code == 200

        archive_response = api_client.post(
            f"/api/v1/knowledge-spaces/{space['id']}/archive",
            headers=tenant_scenario.admin_headers(),
        )
        assert archive_response.status_code == 200
        assert archive_response.json()["status"] == "archived"

    def test_grant_and_manage_restricted_space_membership_for_new_member(
        self, api_client: TestClient, tenant_scenario: TenantScenario
    ) -> None:

        roles_response = api_client.get("/api/v1/roles", headers=tenant_scenario.admin_headers())
        org_admin_role_id = next(
            role["id"] for role in roles_response.json() if role["code"] == "organization_admin"
        )
        assign_response = api_client.post(
            "/api/v1/roles/assignments",
            json={
                "membership_id": str(tenant_scenario.viewer_membership_id),
                "role_id": org_admin_role_id,
                "knowledge_space_id": str(tenant_scenario.restricted_knowledge_space_id),
            },
            headers=tenant_scenario.admin_headers(),
        )
        assert assign_response.status_code == 201

        viewer_get = api_client.get(
            f"/api/v1/knowledge-spaces/{tenant_scenario.restricted_knowledge_space_id}",
            headers=tenant_scenario.viewer_headers(),
        )
        assert viewer_get.status_code == 200

        list_memberships_response = api_client.get(
            f"/api/v1/knowledge-spaces/{tenant_scenario.restricted_knowledge_space_id}/memberships",
            headers=tenant_scenario.viewer_headers(),
        )
        assert list_memberships_response.status_code == 200
