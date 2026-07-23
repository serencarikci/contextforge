"""Unit tests for RequestContext permission helpers and knowledge-space visibility."""

from __future__ import annotations

from uuid import uuid4

import pytest

from contextforge.application.context.request_context import RequestContext
from contextforge.domain.exceptions.identity import AuthorizationError, ResourceNotFoundError
from contextforge.modules.identity_access.domain.enums import PreferredLanguage


def _make_context(**overrides: object) -> RequestContext:
    defaults: dict[str, object] = {
        "correlation_id": "test-correlation",
        "user_id": uuid4(),
        "organization_id": uuid4(),
        "organization_membership_id": uuid4(),
        "preferred_language": PreferredLanguage.EN,
        "permissions": frozenset(),
    }
    defaults.update(overrides)
    return RequestContext(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
@pytest.mark.authorization
class TestPermissionHelpers:
    def test_has_permission_true_when_granted(self) -> None:
        ctx = _make_context(permissions=frozenset({"customer:read"}))
        assert ctx.has_permission("customer:read") is True

    def test_has_permission_false_when_missing(self) -> None:
        ctx = _make_context(permissions=frozenset({"customer:read"}))
        assert ctx.has_permission("customer:create") is False

    def test_platform_admin_bypasses_permission_checks(self) -> None:
        ctx = _make_context(permissions=frozenset(), is_platform_admin=True)
        assert ctx.has_permission("anything:whatsoever") is True

    def test_require_permission_passes_when_granted(self) -> None:
        ctx = _make_context(permissions=frozenset({"customer:create"}))
        ctx.require_permission("customer:create")

    def test_require_permission_raises_when_missing(self) -> None:
        ctx = _make_context(permissions=frozenset())
        with pytest.raises(AuthorizationError):
            ctx.require_permission("customer:create")

    def test_require_permission_platform_admin_never_raises(self) -> None:
        ctx = _make_context(permissions=frozenset(), is_platform_admin=True)
        ctx.require_permission("customer:create")


@pytest.mark.unit
@pytest.mark.authorization
class TestProjectAccess:
    def test_can_access_project_true_with_project_read_permission(self) -> None:
        ctx = _make_context(permissions=frozenset({"project:read"}))
        assert ctx.can_access_project(uuid4()) is True

    def test_can_access_project_false_without_permission(self) -> None:
        ctx = _make_context(permissions=frozenset())
        assert ctx.can_access_project(uuid4()) is False

    def test_platform_admin_can_access_any_project(self) -> None:
        ctx = _make_context(permissions=frozenset(), is_platform_admin=True)
        assert ctx.can_access_project(uuid4()) is True


@pytest.mark.unit
@pytest.mark.authorization
class TestKnowledgeSpaceVisibility:
    def test_platform_admin_can_access_any_knowledge_space(self) -> None:
        ctx = _make_context(is_platform_admin=True)
        assert ctx.can_access_knowledge_space(uuid4()) is True

    def test_explicit_access_grants_visibility_regardless_of_permission(self) -> None:
        ks_id = uuid4()
        ctx = _make_context(
            permissions=frozenset(),
            accessible_knowledge_space_ids=frozenset({ks_id}),
        )
        assert ctx.can_access_knowledge_space(ks_id) is True

    def test_organization_visible_space_requires_read_permission(self) -> None:
        ks_id = uuid4()
        ctx_with_permission = _make_context(
            permissions=frozenset({"knowledge_space:read"}),
            organization_visible_knowledge_space_ids=frozenset({ks_id}),
        )
        assert ctx_with_permission.can_access_knowledge_space(ks_id) is True

        ctx_without_permission = _make_context(
            permissions=frozenset(),
            organization_visible_knowledge_space_ids=frozenset({ks_id}),
        )
        assert ctx_without_permission.can_access_knowledge_space(ks_id) is False

    def test_restricted_space_denied_without_explicit_access(self) -> None:
        ks_id = uuid4()
        ctx = _make_context(permissions=frozenset({"knowledge_space:read"}))

        assert ctx.can_access_knowledge_space(ks_id) is False

    def test_require_knowledge_space_access_raises_not_found_when_denied(self) -> None:
        ctx = _make_context(permissions=frozenset())
        with pytest.raises(ResourceNotFoundError):
            ctx.require_knowledge_space_access(uuid4())

    def test_require_knowledge_space_access_passes_when_granted(self) -> None:
        ks_id = uuid4()
        ctx = _make_context(accessible_knowledge_space_ids=frozenset({ks_id}))
        ctx.require_knowledge_space_access(ks_id)
