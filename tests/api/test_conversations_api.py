from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from tests.helpers import create_conversation, create_knowledge_space, seed_grounding_content

from contextforge.bootstrap.app_factory import create_app
from contextforge.shared.config.settings import Settings, clear_settings_cache

if TYPE_CHECKING:
    from tests.conftest import TenantScenario


@pytest.mark.api
def test_conversation_requires_identity(api_client: TestClient) -> None:
    response = api_client.post("/api/v1/conversations", json={"title": "No auth"})
    assert response.status_code == 401


@pytest.mark.api
def test_conversation_full_lifecycle_and_messaging(
    integration_settings: Settings, tenant_scenario: TenantScenario
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    headers = tenant_scenario.admin_headers()

    with TestClient(app) as api_client:
        ks_id = create_knowledge_space(api_client, headers)
        seed_grounding_content(
            app,
            api_client,
            headers,
            organization_id=tenant_scenario.organization_id,
            knowledge_space_id=ks_id,
        )

        conversation = create_conversation(api_client, headers, ks_id)
        conversation_id = conversation["id"]
        assert conversation["title"] == "Leave questions"
        assert conversation["status"] == "active"

        send_response = api_client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=headers,
            json={"content": "How many annual leave days do employees get?"},
        )
        assert send_response.status_code == 200, send_response.text
        answer = send_response.json()
        assert answer["user_message"]["role"] == "user"
        assert answer["assistant_message"]["role"] == "assistant"
        assert answer["assistant_message"]["status"] == "completed"
        assert answer["assistant_message"]["citations"]
        assert answer["assistant_message"]["citations"][0]["document_title"] == "Leave Policy"

        list_response = api_client.get(
            f"/api/v1/conversations/{conversation_id}/messages", headers=headers
        )
        assert list_response.status_code == 200
        items = list_response.json()["items"]
        assert len(items) == 2

        get_response = api_client.get(f"/api/v1/conversations/{conversation_id}", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["id"] == conversation_id

        patch_response = api_client.patch(
            f"/api/v1/conversations/{conversation_id}",
            headers=headers,
            json={"title": "Renamed conversation", "pinned": True},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["title"] == "Renamed conversation"
        assert patch_response.json()["pinned"] is True

        archive_response = api_client.post(
            f"/api/v1/conversations/{conversation_id}/archive", headers=headers
        )
        assert archive_response.status_code == 200
        assert archive_response.json()["status"] == "archived"

        restore_response = api_client.post(
            f"/api/v1/conversations/{conversation_id}/restore", headers=headers
        )
        assert restore_response.status_code == 200
        assert restore_response.json()["status"] == "active"

        delete_response = api_client.delete(
            f"/api/v1/conversations/{conversation_id}", headers=headers
        )
        assert delete_response.status_code == 204

        after_delete = api_client.get(f"/api/v1/conversations/{conversation_id}", headers=headers)
        assert after_delete.status_code == 404


@pytest.mark.api
def test_message_idempotency_key_replays_same_answer(
    integration_settings: Settings, tenant_scenario: TenantScenario
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    headers = tenant_scenario.admin_headers()

    with TestClient(app) as api_client:
        ks_id = create_knowledge_space(api_client, headers)
        seed_grounding_content(
            app,
            api_client,
            headers,
            organization_id=tenant_scenario.organization_id,
            knowledge_space_id=ks_id,
        )
        conversation = create_conversation(api_client, headers, ks_id)
        idempotency_key = f"idem-{uuid4().hex}"

        first = api_client.post(
            f"/api/v1/conversations/{conversation['id']}/messages",
            headers={**headers, "Idempotency-Key": idempotency_key},
            json={"content": "How many annual leave days do employees get?"},
        )
        second = api_client.post(
            f"/api/v1/conversations/{conversation['id']}/messages",
            headers={**headers, "Idempotency-Key": idempotency_key},
            json={"content": "How many annual leave days do employees get?"},
        )
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["assistant_message"]["id"] == second.json()["assistant_message"]["id"]


@pytest.mark.api
def test_streaming_message_emits_expected_sse_events(
    integration_settings: Settings, tenant_scenario: TenantScenario
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    headers = tenant_scenario.admin_headers()

    with TestClient(app) as api_client:
        ks_id = create_knowledge_space(api_client, headers)
        seed_grounding_content(
            app,
            api_client,
            headers,
            organization_id=tenant_scenario.organization_id,
            knowledge_space_id=ks_id,
        )
        conversation = create_conversation(api_client, headers, ks_id)

        response = api_client.post(
            f"/api/v1/conversations/{conversation['id']}/messages/stream",
            headers=headers,
            json={"content": "How many annual leave days do employees get?"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        assert "event: stream.started" in response.text
        assert "event: generation.completed" in response.text


@pytest.mark.api
def test_feedback_submission_and_listing(
    integration_settings: Settings, tenant_scenario: TenantScenario
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    headers = tenant_scenario.admin_headers()

    with TestClient(app) as api_client:
        ks_id = create_knowledge_space(api_client, headers)
        seed_grounding_content(
            app,
            api_client,
            headers,
            organization_id=tenant_scenario.organization_id,
            knowledge_space_id=ks_id,
        )
        conversation = create_conversation(api_client, headers, ks_id)
        send_response = api_client.post(
            f"/api/v1/conversations/{conversation['id']}/messages",
            headers=headers,
            json={"content": "How many annual leave days do employees get?"},
        )
        assistant_message_id = send_response.json()["assistant_message"]["id"]

        feedback_response = api_client.put(
            f"/api/v1/messages/{assistant_message_id}/feedback",
            headers=headers,
            json={"rating": "up", "score": 5, "comment": "Very helpful"},
        )
        assert feedback_response.status_code == 200, feedback_response.text
        assert feedback_response.json()["rating"] == "up"

        updated_response = api_client.put(
            f"/api/v1/messages/{assistant_message_id}/feedback",
            headers=headers,
            json={"rating": "down", "category": "incomplete"},
        )
        assert updated_response.status_code == 200
        assert updated_response.json()["rating"] == "down"


@pytest.mark.api
def test_conversation_export_json(
    integration_settings: Settings, tenant_scenario: TenantScenario
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    headers = tenant_scenario.admin_headers()

    with TestClient(app) as api_client:
        ks_id = create_knowledge_space(api_client, headers)
        seed_grounding_content(
            app,
            api_client,
            headers,
            organization_id=tenant_scenario.organization_id,
            knowledge_space_id=ks_id,
        )
        conversation = create_conversation(api_client, headers, ks_id)
        api_client.post(
            f"/api/v1/conversations/{conversation['id']}/messages",
            headers=headers,
            json={"content": "How many annual leave days do employees get?"},
        )

        export_response = api_client.get(
            f"/api/v1/conversations/{conversation['id']}/export?format=json", headers=headers
        )
        assert export_response.status_code == 200
        body = export_response.json()
        assert body["conversation_id"] == conversation["id"]
        assert len(body["messages"]) == 2

        markdown_response = api_client.get(
            f"/api/v1/conversations/{conversation['id']}/export?format=markdown", headers=headers
        )
        assert markdown_response.status_code == 200
        assert "text/markdown" in markdown_response.headers.get("content-type", "")
        assert "Leave questions" in markdown_response.text


@pytest.mark.api
def test_conversation_suggestions_returns_fallback_questions(
    integration_settings: Settings, tenant_scenario: TenantScenario
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    headers = tenant_scenario.admin_headers()

    with TestClient(app) as api_client:
        ks_id = create_knowledge_space(api_client, headers)
        seed_grounding_content(
            app,
            api_client,
            headers,
            organization_id=tenant_scenario.organization_id,
            knowledge_space_id=ks_id,
        )
        conversation = create_conversation(api_client, headers, ks_id)
        api_client.post(
            f"/api/v1/conversations/{conversation['id']}/messages",
            headers=headers,
            json={"content": "How many annual leave days do employees get?"},
        )

        response = api_client.get(
            f"/api/v1/conversations/{conversation['id']}/suggestions", headers=headers
        )
        assert response.status_code == 200
        suggestions = response.json()["suggestions"]
        assert 1 <= len(suggestions) <= 10


@pytest.mark.api
def test_conversation_participants_lifecycle(
    integration_settings: Settings, tenant_scenario: TenantScenario
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    headers = tenant_scenario.admin_headers()

    with TestClient(app) as api_client:
        ks_id = create_knowledge_space(api_client, headers)
        conversation = create_conversation(api_client, headers, ks_id)

        add_response = api_client.post(
            f"/api/v1/conversations/{conversation['id']}/participants",
            headers=headers,
            json={"user_id": str(tenant_scenario.viewer_user_id), "role": "participant"},
        )
        assert add_response.status_code == 201, add_response.text

        list_response = api_client.get(
            f"/api/v1/conversations/{conversation['id']}/participants", headers=headers
        )
        assert list_response.status_code == 200
        user_ids = {item["user_id"] for item in list_response.json()}
        assert str(tenant_scenario.viewer_user_id) in user_ids

        viewer_get = api_client.get(
            f"/api/v1/conversations/{conversation['id']}", headers=tenant_scenario.viewer_headers()
        )
        assert viewer_get.status_code == 200

        remove_response = api_client.delete(
            f"/api/v1/conversations/{conversation['id']}/participants/"
            f"{tenant_scenario.viewer_user_id}",
            headers=headers,
        )
        assert remove_response.status_code == 204
