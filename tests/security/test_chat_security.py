from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from tests.helpers import create_conversation, create_knowledge_space, seed_grounding_content

from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.bootstrap.app_factory import create_app
from contextforge.shared.config.settings import Settings, clear_settings_cache

if TYPE_CHECKING:
    from tests.conftest import TenantScenario

    from contextforge.infrastructure.database.session import DatabaseManager


@pytest_asyncio.fixture
async def _admin_granted_restricted_ks_access(
    db_manager: DatabaseManager,
    integration_settings: Settings,
    tenant_scenario: TenantScenario,
) -> None:
    from contextforge.modules.identity_access.application.services.identity_context_service import (
        build_request_context,
    )
    from contextforge.modules.identity_access.application.services.role_service import (
        RoleService,
    )
    from contextforge.modules.identity_access.domain.enums import SystemRoleCode

    async with SqlAlchemyUnitOfWork(db_manager.session_factory) as uow:
        admin_ctx = await build_request_context(
            uow,
            settings=integration_settings,
            user_id=tenant_scenario.admin_user_id,
            organization_id=tenant_scenario.organization_id,
        )
        admin_membership = await uow.memberships.get_by_org_and_user(
            tenant_scenario.organization_id, tenant_scenario.admin_user_id
        )
    assert admin_membership is not None

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    roles = await RoleService().list_roles(uow, admin_ctx)
    viewer_role = next(role for role in roles if role.code == SystemRoleCode.VIEWER.value)

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    await RoleService().assign_role(
        uow,
        admin_ctx,
        membership_id=admin_membership.id,
        role_id=viewer_role.id,
        knowledge_space_id=tenant_scenario.restricted_knowledge_space_id,
    )


@pytest.mark.security
def test_conversation_requires_identity(api_client: TestClient) -> None:
    response = api_client.get(f"/api/v1/conversations/{uuid4()}")
    assert response.status_code == 401


@pytest.mark.security
def test_cross_tenant_conversation_access_is_not_found(
    integration_settings: Settings,
    tenant_scenario: TenantScenario,
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    with TestClient(app) as api_client:
        conversation_id = create_conversation(api_client, tenant_scenario.admin_headers())["id"]

        response = api_client.get(
            f"/api/v1/conversations/{conversation_id}",
            headers=tenant_scenario.other_org_admin_headers(),
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.security
def test_non_owner_non_participant_cannot_read_conversation(
    integration_settings: Settings, tenant_scenario: TenantScenario
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    with TestClient(app) as api_client:
        conversation_id = create_conversation(api_client, tenant_scenario.admin_headers())["id"]

        response = api_client.get(
            f"/api/v1/conversations/{conversation_id}",
            headers=tenant_scenario.viewer_headers(),
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.security
def test_participant_gains_and_loses_access(
    integration_settings: Settings, tenant_scenario: TenantScenario
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    admin_headers = tenant_scenario.admin_headers()
    viewer_headers = tenant_scenario.viewer_headers()
    with TestClient(app) as api_client:
        conversation_id = create_conversation(api_client, admin_headers)["id"]

        add_response = api_client.post(
            f"/api/v1/conversations/{conversation_id}/participants",
            headers=admin_headers,
            json={"user_id": str(tenant_scenario.viewer_user_id)},
        )
        assert add_response.status_code == 201

        granted = api_client.get(f"/api/v1/conversations/{conversation_id}", headers=viewer_headers)
        assert granted.status_code == 200

        remove_response = api_client.delete(
            f"/api/v1/conversations/{conversation_id}/participants/"
            f"{tenant_scenario.viewer_user_id}",
            headers=admin_headers,
        )
        assert remove_response.status_code == 204

        revoked = api_client.get(f"/api/v1/conversations/{conversation_id}", headers=viewer_headers)
        assert revoked.status_code == 404


@pytest.mark.security
def test_non_owner_cannot_manage_participants(
    integration_settings: Settings, tenant_scenario: TenantScenario
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    admin_headers = tenant_scenario.admin_headers()
    viewer_headers = tenant_scenario.viewer_headers()
    with TestClient(app) as api_client:
        conversation_id = create_conversation(api_client, admin_headers)["id"]
        api_client.post(
            f"/api/v1/conversations/{conversation_id}/participants",
            headers=admin_headers,
            json={"user_id": str(tenant_scenario.viewer_user_id)},
        )

        response = api_client.post(
            f"/api/v1/conversations/{conversation_id}/participants",
            headers=viewer_headers,
            json={"user_id": str(uuid4())},
        )
        assert response.status_code == 404


@pytest.mark.security
def test_message_fails_gracefully_when_linked_knowledge_space_becomes_inaccessible(
    integration_settings: Settings,
    tenant_scenario: TenantScenario,
    _admin_granted_restricted_ks_access: None,
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    admin_headers = tenant_scenario.admin_headers()
    viewer_headers = tenant_scenario.viewer_headers()
    with TestClient(app) as api_client:
        conversation_id = create_conversation(api_client, admin_headers)["id"]
        link_response = api_client.post(
            f"/api/v1/conversations/{conversation_id}/knowledge-spaces",
            headers=admin_headers,
            json={"knowledge_space_id": str(tenant_scenario.restricted_knowledge_space_id)},
        )
        assert link_response.status_code == 204

        add_participant = api_client.post(
            f"/api/v1/conversations/{conversation_id}/participants",
            headers=admin_headers,
            json={"user_id": str(tenant_scenario.viewer_user_id)},
        )
        assert add_participant.status_code == 201

        send_response = api_client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=viewer_headers,
            json={"content": "What does the restricted playbook say?"},
        )
        assert send_response.status_code == 200
        assistant_message = send_response.json()["assistant_message"]
        assert assistant_message["status"] == "failed"
        assert assistant_message["error_code"] == "NO_ACCESSIBLE_KNOWLEDGE_SPACES"


@pytest.mark.security
def test_chat_analytics_requires_manage_permission(
    integration_settings: Settings, tenant_scenario: TenantScenario
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    with TestClient(app) as api_client:
        viewer_response = api_client.get(
            "/api/v1/chat/analytics/overview", headers=tenant_scenario.viewer_headers()
        )
        assert viewer_response.status_code == 403

        admin_response = api_client.get(
            "/api/v1/chat/analytics/overview", headers=tenant_scenario.admin_headers()
        )
        assert admin_response.status_code == 200


@pytest.mark.security
def test_feedback_requires_ownership_or_participation(
    integration_settings: Settings, tenant_scenario: TenantScenario
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    admin_headers = tenant_scenario.admin_headers()
    viewer_headers = tenant_scenario.viewer_headers()
    with TestClient(app) as api_client:
        ks_id = create_knowledge_space(api_client, admin_headers)
        seed_grounding_content(
            app,
            api_client,
            admin_headers,
            organization_id=tenant_scenario.organization_id,
            knowledge_space_id=ks_id,
        )
        conversation = api_client.post(
            "/api/v1/conversations",
            headers=admin_headers,
            json={"title": "Feedback test", "knowledge_space_ids": [str(ks_id)]},
        ).json()

        send_response = api_client.post(
            f"/api/v1/conversations/{conversation['id']}/messages",
            headers=admin_headers,
            json={"content": "Anything grounded here?"},
        )
        assistant_message_id = send_response.json()["assistant_message"]["id"]

        response = api_client.put(
            f"/api/v1/messages/{assistant_message_id}/feedback",
            headers=viewer_headers,
            json={"rating": "down"},
        )
        assert response.status_code == 404
