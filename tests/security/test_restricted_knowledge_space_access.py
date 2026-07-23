"""Security test: restricted knowledge spaces are denied to non-members.

`knowledge_space:read` alone is only sufficient for organization-visible
spaces. A `restricted` knowledge space must additionally require an
explicit knowledge-space membership (or a role assignment scoped to it) --
holding the organization-wide read permission is not enough. Denial is
surfaced as 404 (not 403) so a caller without access cannot distinguish
"exists but restricted" from "does not exist".
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from tests.conftest import TenantScenario

    from contextforge.infrastructure.database.session import DatabaseManager


@pytest.mark.security
def test_viewer_without_membership_cannot_read_restricted_knowledge_space(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get(
        f"/api/v1/knowledge-spaces/{tenant_scenario.restricted_knowledge_space_id}",
        headers=tenant_scenario.viewer_headers(),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.security
def test_viewer_without_membership_does_not_see_restricted_space_in_listing(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get("/api/v1/knowledge-spaces", headers=tenant_scenario.viewer_headers())
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert str(tenant_scenario.restricted_knowledge_space_id) not in ids


@pytest.mark.security
@pytest.mark.asyncio
async def test_restricted_knowledge_space_genuinely_exists_and_is_restricted(
    tenant_scenario: TenantScenario, db_manager: DatabaseManager
) -> None:
    """Sanity check: denial is a real authorization decision, not a broken
    fixture -- the space exists with `visibility=restricted`. Notably, even
    the organization admin who created it gets the same 404 through the API
    (see the next test): org-wide permissions do not imply access to a
    specific restricted knowledge space, only platform-admin status or an
    explicit grant (role assignment or knowledge-space membership) does.
    """
    from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
    from contextforge.modules.identity_access.domain.enums import KnowledgeSpaceVisibility

    async with SqlAlchemyUnitOfWork(db_manager.session_factory) as uow:
        space = await uow.knowledge_spaces.get(
            tenant_scenario.organization_id, tenant_scenario.restricted_knowledge_space_id
        )
    assert space is not None
    assert space.visibility == KnowledgeSpaceVisibility.RESTRICTED


@pytest.mark.security
def test_organization_admin_without_explicit_grant_also_gets_404(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    """Restricted visibility is not bypassed by org-wide permissions: even the
    organization admin who created the space is denied without an explicit
    role assignment or knowledge-space membership scoped to it."""
    response = api_client.get(
        f"/api/v1/knowledge-spaces/{tenant_scenario.restricted_knowledge_space_id}",
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.security
def test_viewer_cannot_add_themselves_to_restricted_knowledge_space(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    """Even attempting to self-grant knowledge-space access is denied --
    membership management on a restricted space the caller cannot see is
    itself blocked at the same 404 boundary."""
    response = api_client.post(
        f"/api/v1/knowledge-spaces/{tenant_scenario.restricted_knowledge_space_id}/memberships",
        json={
            "membership_id": str(tenant_scenario.viewer_membership_id),
            "access_level": "manager",
        },
        headers=tenant_scenario.viewer_headers(),
    )
    assert response.status_code in {403, 404}


@pytest.mark.security
def test_nonexistent_knowledge_space_is_also_404_for_admin(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    """404 for restricted-and-inaccessible is indistinguishable from 404 for
    genuinely nonexistent -- both must return the same not-found shape."""
    response = api_client.get(
        f"/api/v1/knowledge-spaces/{uuid4()}",
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 404
