"""Typed request context for authorization decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from contextforge.domain.exceptions.identity import AuthorizationError, ResourceNotFoundError
from contextforge.modules.identity_access.domain.enums import PreferredLanguage


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Application-level identity and authorization context."""

    correlation_id: str
    user_id: UUID
    organization_id: UUID
    organization_membership_id: UUID
    preferred_language: PreferredLanguage
    permissions: frozenset[str]
    project_id: UUID | None = None
    knowledge_space_id: UUID | None = None
    is_platform_admin: bool = False
    accessible_project_ids: frozenset[UUID] = field(default_factory=frozenset)
    accessible_knowledge_space_ids: frozenset[UUID] = field(default_factory=frozenset)
    organization_visible_knowledge_space_ids: frozenset[UUID] = field(default_factory=frozenset)

    def has_permission(self, permission_code: str) -> bool:
        if self.is_platform_admin:
            return True
        return permission_code in self.permissions

    def require_permission(self, permission_code: str) -> None:
        if not self.has_permission(permission_code):
            raise AuthorizationError(
                "You do not have permission to perform this action.",
                code="PERMISSION_DENIED",
            )

    def can_access_project(self, project_id: UUID) -> bool:

        if self.is_platform_admin:
            return True
        return self.has_permission("project:read")

    def can_access_knowledge_space(self, knowledge_space_id: UUID) -> bool:
        if self.is_platform_admin:
            return True
        if knowledge_space_id in self.accessible_knowledge_space_ids:
            return True
        if knowledge_space_id in self.organization_visible_knowledge_space_ids:
            return self.has_permission("knowledge_space:read")
        return False

    def require_knowledge_space_access(self, knowledge_space_id: UUID) -> None:
        if not self.can_access_knowledge_space(knowledge_space_id):
            raise ResourceNotFoundError("Knowledge space not found.")
