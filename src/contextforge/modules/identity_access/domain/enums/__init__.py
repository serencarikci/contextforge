"""Shared domain enums for identity and knowledge modules."""

from __future__ import annotations

from enum import StrEnum


class OrganizationStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class UserStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class PreferredLanguage(StrEnum):
    TR = "tr"
    EN = "en"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REMOVED = "removed"


class CustomerStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    ARCHIVED = "archived"


class KnowledgeSpaceVisibility(StrEnum):
    ORGANIZATION = "organization"
    RESTRICTED = "restricted"


class KnowledgeSpaceStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class KnowledgeSpaceAccessLevel(StrEnum):
    READER = "reader"
    CONTRIBUTOR = "contributor"
    MANAGER = "manager"


class SystemRoleCode(StrEnum):
    PLATFORM_ADMIN = "platform_admin"
    ORGANIZATION_ADMIN = "organization_admin"
    PROJECT_MANAGER = "project_manager"
    DEVELOPER = "developer"
    SUPPORT_AGENT = "support_agent"
    KNOWLEDGE_MANAGER = "knowledge_manager"
    VIEWER = "viewer"


class PermissionCode(StrEnum):
    ORGANIZATION_READ = "organization:read"
    ORGANIZATION_UPDATE = "organization:update"
    ORGANIZATION_MANAGE_MEMBERS = "organization:manage_members"
    USER_READ = "user:read"
    USER_MANAGE = "user:manage"
    ROLE_READ = "role:read"
    ROLE_MANAGE = "role:manage"
    CUSTOMER_CREATE = "customer:create"
    CUSTOMER_READ = "customer:read"
    CUSTOMER_UPDATE = "customer:update"
    CUSTOMER_ARCHIVE = "customer:archive"
    PROJECT_CREATE = "project:create"
    PROJECT_READ = "project:read"
    PROJECT_UPDATE = "project:update"
    PROJECT_ARCHIVE = "project:archive"
    PROJECT_MANAGE_MEMBERS = "project:manage_members"
    KNOWLEDGE_SPACE_CREATE = "knowledge_space:create"
    KNOWLEDGE_SPACE_READ = "knowledge_space:read"
    KNOWLEDGE_SPACE_UPDATE = "knowledge_space:update"
    KNOWLEDGE_SPACE_ARCHIVE = "knowledge_space:archive"
    KNOWLEDGE_SPACE_MANAGE_MEMBERS = "knowledge_space:manage_members"
    AUDIT_READ = "audit:read"
