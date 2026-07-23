"""Canonical system permission/role seed definitions."""

from __future__ import annotations

import uuid

from contextforge.modules.identity_access.domain.enums import PermissionCode, SystemRoleCode

RBAC_UUID_NAMESPACE = uuid.UUID("6f2a9b4e-2c3f-4b8a-9d1e-8a2b6f4c1e3a")


def permission_id(code: str) -> uuid.UUID:
    """Deterministic UUID for a permission code."""
    return uuid.uuid5(RBAC_UUID_NAMESPACE, f"permission:{code}")


def system_role_id(code: str) -> uuid.UUID:
    """Deterministic UUID for a system role code."""
    return uuid.uuid5(RBAC_UUID_NAMESPACE, f"role:{code}")


PERMISSIONS: tuple[tuple[str, str], ...] = (
    (PermissionCode.ORGANIZATION_READ, "Read organization details"),
    (PermissionCode.ORGANIZATION_UPDATE, "Update organization details"),
    (PermissionCode.ORGANIZATION_MANAGE_MEMBERS, "Manage organization memberships"),
    (PermissionCode.USER_READ, "Read user profiles within membership context"),
    (PermissionCode.USER_MANAGE, "Manage user lifecycle within membership context"),
    (PermissionCode.ROLE_READ, "Read roles and assignments"),
    (PermissionCode.ROLE_MANAGE, "Manage organization roles and assignments"),
    (PermissionCode.CUSTOMER_CREATE, "Create customers"),
    (PermissionCode.CUSTOMER_READ, "Read customers"),
    (PermissionCode.CUSTOMER_UPDATE, "Update customers"),
    (PermissionCode.CUSTOMER_ARCHIVE, "Archive customers"),
    (PermissionCode.PROJECT_CREATE, "Create projects"),
    (PermissionCode.PROJECT_READ, "Read projects"),
    (PermissionCode.PROJECT_UPDATE, "Update projects"),
    (PermissionCode.PROJECT_ARCHIVE, "Archive projects"),
    (PermissionCode.PROJECT_MANAGE_MEMBERS, "Manage project-scoped memberships"),
    (PermissionCode.KNOWLEDGE_SPACE_CREATE, "Create knowledge spaces"),
    (PermissionCode.KNOWLEDGE_SPACE_READ, "Read knowledge spaces"),
    (PermissionCode.KNOWLEDGE_SPACE_UPDATE, "Update knowledge spaces"),
    (PermissionCode.KNOWLEDGE_SPACE_ARCHIVE, "Archive knowledge spaces"),
    (PermissionCode.KNOWLEDGE_SPACE_MANAGE_MEMBERS, "Manage knowledge-space memberships"),
    (PermissionCode.DOCUMENT_CREATE, "Create documents"),
    (PermissionCode.DOCUMENT_READ, "Read documents"),
    (PermissionCode.DOCUMENT_UPDATE, "Update documents"),
    (PermissionCode.DOCUMENT_DELETE, "Delete documents"),
    (PermissionCode.AUDIT_READ, "Read audit events"),
)

SYSTEM_ROLES: tuple[tuple[str, str, str], ...] = (
    (SystemRoleCode.PLATFORM_ADMIN, "Platform Admin", "Platform-level administration"),
    (SystemRoleCode.ORGANIZATION_ADMIN, "Organization Admin", "Full organization administration"),
    (SystemRoleCode.PROJECT_MANAGER, "Project Manager", "Manage projects and knowledge spaces"),
    (SystemRoleCode.DEVELOPER, "Developer", "Read project and knowledge resources"),
    (SystemRoleCode.SUPPORT_AGENT, "Support Agent", "Read customer and project context"),
    (SystemRoleCode.KNOWLEDGE_MANAGER, "Knowledge Manager", "Manage knowledge spaces"),
    (SystemRoleCode.VIEWER, "Viewer", "Read-only access to tenant resources"),
)

_ORG_ADMIN_PERMS = tuple(code for code, _ in PERMISSIONS)

_PROJECT_MANAGER_PERMS = (
    PermissionCode.PROJECT_CREATE,
    PermissionCode.PROJECT_READ,
    PermissionCode.PROJECT_UPDATE,
    PermissionCode.PROJECT_ARCHIVE,
    PermissionCode.PROJECT_MANAGE_MEMBERS,
    PermissionCode.CUSTOMER_READ,
    PermissionCode.KNOWLEDGE_SPACE_CREATE,
    PermissionCode.KNOWLEDGE_SPACE_READ,
    PermissionCode.KNOWLEDGE_SPACE_UPDATE,
    PermissionCode.KNOWLEDGE_SPACE_ARCHIVE,
    PermissionCode.KNOWLEDGE_SPACE_MANAGE_MEMBERS,
    PermissionCode.DOCUMENT_CREATE,
    PermissionCode.DOCUMENT_READ,
    PermissionCode.DOCUMENT_UPDATE,
    PermissionCode.DOCUMENT_DELETE,
)

_READ_PERMS = (
    PermissionCode.CUSTOMER_READ,
    PermissionCode.PROJECT_READ,
    PermissionCode.KNOWLEDGE_SPACE_READ,
    PermissionCode.DOCUMENT_READ,
)

_DEVELOPER_PERMS = (
    *_READ_PERMS,
    PermissionCode.DOCUMENT_CREATE,
    PermissionCode.DOCUMENT_UPDATE,
)

_KNOWLEDGE_MANAGER_PERMS = (
    PermissionCode.CUSTOMER_READ,
    PermissionCode.PROJECT_READ,
    PermissionCode.KNOWLEDGE_SPACE_CREATE,
    PermissionCode.KNOWLEDGE_SPACE_READ,
    PermissionCode.KNOWLEDGE_SPACE_UPDATE,
    PermissionCode.KNOWLEDGE_SPACE_ARCHIVE,
    PermissionCode.KNOWLEDGE_SPACE_MANAGE_MEMBERS,
    PermissionCode.DOCUMENT_CREATE,
    PermissionCode.DOCUMENT_READ,
    PermissionCode.DOCUMENT_UPDATE,
    PermissionCode.DOCUMENT_DELETE,
)

ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    SystemRoleCode.PLATFORM_ADMIN: (),
    SystemRoleCode.ORGANIZATION_ADMIN: _ORG_ADMIN_PERMS,
    SystemRoleCode.PROJECT_MANAGER: _PROJECT_MANAGER_PERMS,
    SystemRoleCode.DEVELOPER: _DEVELOPER_PERMS,
    SystemRoleCode.SUPPORT_AGENT: _READ_PERMS,
    SystemRoleCode.KNOWLEDGE_MANAGER: _KNOWLEDGE_MANAGER_PERMS,
    SystemRoleCode.VIEWER: _READ_PERMS,
}
