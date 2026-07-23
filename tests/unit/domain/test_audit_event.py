"""Unit tests for the append-only AuditEvent entity and metadata sanitization."""

from __future__ import annotations

from uuid import uuid4

import pytest

from contextforge.modules.audit.domain.entities.audit_event import AuditEvent


@pytest.mark.unit
class TestAuditEventValidation:
    def test_requires_action(self) -> None:
        with pytest.raises(ValueError, match="Audit action and resource_type are required"):
            AuditEvent(action="", resource_type="customer")

    def test_requires_resource_type(self) -> None:
        with pytest.raises(ValueError, match="Audit action and resource_type are required"):
            AuditEvent(action="customer.created", resource_type="")

    def test_strips_whitespace(self) -> None:
        event = AuditEvent(action=" customer.created ", resource_type=" customer ")
        assert event.action == "customer.created"
        assert event.resource_type == "customer"

    def test_defaults(self) -> None:
        event = AuditEvent(action="customer.created", resource_type="customer")
        assert event.metadata == {}
        assert event.organization_id is None
        assert event.actor_user_id is None
        assert event.resource_id is None


@pytest.mark.unit
class TestAuditEventMetadataSanitization:
    @pytest.mark.parametrize(
        "forbidden_key",
        [
            "password",
            "Password",
            "secret",
            "api_key",
            "access_key",
            "secret_key",
            "token",
            "auth_token",
            "Authorization",
            "cookie",
            "session_cookie",
        ],
    )
    def test_removes_forbidden_keys_case_insensitively(self, forbidden_key: str) -> None:
        event = AuditEvent(
            action="user.created",
            resource_type="user",
            metadata={forbidden_key: "super-secret-value", "email": "user@example.com"},
        )
        assert forbidden_key not in event.metadata
        assert event.metadata == {"email": "user@example.com"}

    def test_preserves_safe_keys(self) -> None:
        event = AuditEvent(
            action="customer.created",
            resource_type="customer",
            metadata={"code": "DEV-CUST", "name": "Demo Customer", "count": 3},
        )
        assert event.metadata == {"code": "DEV-CUST", "name": "Demo Customer", "count": 3}

    def test_sanitize_metadata_is_pure(self) -> None:
        raw = {"password": "x", "code": "DEV-CUST"}
        sanitized = AuditEvent.sanitize_metadata(raw)
        assert sanitized == {"code": "DEV-CUST"}

        assert raw == {"password": "x", "code": "DEV-CUST"}

    def test_removes_keys_that_merely_contain_forbidden_substring(self) -> None:

        event = AuditEvent(
            action="user.created",
            resource_type="user",
            metadata={"user_password_hint": "abc", "display_name": "Dev Admin"},
        )
        assert "user_password_hint" not in event.metadata
        assert event.metadata == {"display_name": "Dev Admin"}

    def test_correlation_and_resource_ids_are_preserved(self) -> None:
        resource_id = uuid4()
        correlation_id = uuid4()
        actor_id = uuid4()
        org_id = uuid4()
        event = AuditEvent(
            action="customer.created",
            resource_type="customer",
            organization_id=org_id,
            actor_user_id=actor_id,
            resource_id=resource_id,
            correlation_id=correlation_id,
        )
        assert event.organization_id == org_id
        assert event.actor_user_id == actor_id
        assert event.resource_id == resource_id
        assert event.correlation_id == correlation_id
