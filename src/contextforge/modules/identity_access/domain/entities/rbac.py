"""Role, permission, and role assignment entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from contextforge.domain.exceptions.identity import InvalidResourceStateError
from contextforge.modules.identity_access.domain.value_objects import (
    RoleCode,
    validate_permission_code,
)
from contextforge.shared.utilities.datetime import utc_now


@dataclass(slots=True)
class Permission:
    code: str
    description: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.code = validate_permission_code(self.code)


@dataclass(slots=True)
class Role:
    code: str
    name: str
    organization_id: UUID | None = None
    description: str | None = None
    is_system: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.code = RoleCode(self.code).value
        self.name = self.name.strip()
        if not self.name:
            msg = "Role name is required"
            raise ValueError(msg)
        if self.is_system and self.organization_id is not None:
            msg = "System roles must not have organization_id"
            raise ValueError(msg)
        if not self.is_system and self.organization_id is None:
            msg = "Organization roles require organization_id"
            raise ValueError(msg)

    def update(self, *, name: str | None = None, description: str | None = None) -> None:
        if self.is_system:
            raise InvalidResourceStateError("System roles cannot be modified.")
        if name is not None:
            cleaned = name.strip()
            if not cleaned:
                msg = "Role name is required"
                raise ValueError(msg)
            self.name = cleaned
        if description is not None:
            self.description = description
        self.updated_at = utc_now()


@dataclass(slots=True)
class RoleAssignment:
    organization_id: UUID
    membership_id: UUID
    role_id: UUID
    id: UUID = field(default_factory=uuid4)
    project_id: UUID | None = None
    knowledge_space_id: UUID | None = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self._validate_scope()

    def _validate_scope(self) -> None:
        has_project = self.project_id is not None
        has_ks = self.knowledge_space_id is not None
        if has_project and has_ks:
            raise InvalidResourceStateError(
                "Role assignment cannot target both project and knowledge space."
            )

    @property
    def is_organization_scope(self) -> bool:
        return self.project_id is None and self.knowledge_space_id is None

    @property
    def is_project_scope(self) -> bool:
        return self.project_id is not None and self.knowledge_space_id is None

    @property
    def is_knowledge_space_scope(self) -> bool:
        return self.knowledge_space_id is not None and self.project_id is None
