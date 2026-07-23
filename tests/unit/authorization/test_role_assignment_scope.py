"""Unit tests for RoleAssignment scope invariants."""

from __future__ import annotations

from uuid import uuid4

import pytest

from contextforge.domain.exceptions.identity import InvalidResourceStateError
from contextforge.modules.identity_access.domain.entities.rbac import (
    Permission,
    Role,
    RoleAssignment,
)


@pytest.mark.unit
@pytest.mark.authorization
class TestRoleAssignmentScope:
    def test_organization_scope_when_no_project_or_ks(self) -> None:
        assignment = RoleAssignment(organization_id=uuid4(), membership_id=uuid4(), role_id=uuid4())
        assert assignment.is_organization_scope is True
        assert assignment.is_project_scope is False
        assert assignment.is_knowledge_space_scope is False

    def test_project_scope_when_project_id_set(self) -> None:
        assignment = RoleAssignment(
            organization_id=uuid4(),
            membership_id=uuid4(),
            role_id=uuid4(),
            project_id=uuid4(),
        )
        assert assignment.is_organization_scope is False
        assert assignment.is_project_scope is True
        assert assignment.is_knowledge_space_scope is False

    def test_knowledge_space_scope_when_ks_id_set(self) -> None:
        assignment = RoleAssignment(
            organization_id=uuid4(),
            membership_id=uuid4(),
            role_id=uuid4(),
            knowledge_space_id=uuid4(),
        )
        assert assignment.is_organization_scope is False
        assert assignment.is_project_scope is False
        assert assignment.is_knowledge_space_scope is True

    def test_cannot_target_both_project_and_knowledge_space(self) -> None:
        with pytest.raises(InvalidResourceStateError, match="cannot target both"):
            RoleAssignment(
                organization_id=uuid4(),
                membership_id=uuid4(),
                role_id=uuid4(),
                project_id=uuid4(),
                knowledge_space_id=uuid4(),
            )


@pytest.mark.unit
@pytest.mark.authorization
class TestRoleInvariants:
    def test_system_role_requires_no_organization_id(self) -> None:
        with pytest.raises(ValueError, match="System roles must not have organization_id"):
            Role(code="viewer", name="Viewer", organization_id=uuid4(), is_system=True)

    def test_organization_role_requires_organization_id(self) -> None:
        with pytest.raises(ValueError, match="Organization roles require organization_id"):
            Role(code="custom_role", name="Custom Role", is_system=False)

    def test_system_role_cannot_be_updated(self) -> None:
        role = Role(code="viewer", name="Viewer", is_system=True)
        with pytest.raises(InvalidResourceStateError):
            role.update(name="New Name")

    def test_organization_role_can_be_updated(self) -> None:
        role = Role(
            code="custom_role", name="Custom Role", organization_id=uuid4(), is_system=False
        )
        role.update(name="Renamed Role")
        assert role.name == "Renamed Role"

    def test_role_requires_non_empty_name(self) -> None:
        with pytest.raises(ValueError, match="Role name is required"):
            Role(code="custom_role", name="   ", organization_id=uuid4())


@pytest.mark.unit
@pytest.mark.authorization
class TestPermissionValidation:
    def test_valid_permission_code(self) -> None:
        permission = Permission(code="customer:read", description="Read customers")
        assert permission.code == "customer:read"

    def test_invalid_permission_code_raises(self) -> None:
        with pytest.raises(ValueError, match="Permission code"):
            Permission(code="invalid-code", description="Broken")
