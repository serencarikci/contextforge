"""Project entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from contextforge.domain.exceptions.identity import InvalidResourceStateError
from contextforge.modules.identity_access.domain.enums import PreferredLanguage, ProjectStatus
from contextforge.modules.identity_access.domain.value_objects import ProjectKey
from contextforge.shared.utilities.datetime import utc_now


@dataclass(slots=True)
class Project:
    organization_id: UUID
    name: str
    key: str
    id: UUID = field(default_factory=uuid4)
    customer_id: UUID | None = None
    description: str | None = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    default_language: PreferredLanguage = PreferredLanguage.EN
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    archived_at: datetime | None = None

    def __post_init__(self) -> None:
        self.name = self._validate_name(self.name)
        self.key = ProjectKey(self.key).value

    @staticmethod
    def _validate_name(name: str) -> str:
        cleaned = name.strip()
        if len(cleaned) < 2 or len(cleaned) > 200:
            msg = "Project name must be between 2 and 200 characters"
            raise ValueError(msg)
        return cleaned

    def update(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        default_language: PreferredLanguage | None = None,
        status: ProjectStatus | None = None,
    ) -> None:
        if self.status == ProjectStatus.ARCHIVED:
            raise InvalidResourceStateError("Archived projects cannot be updated.")
        if name is not None:
            self.name = self._validate_name(name)
        if description is not None:
            self.description = description
        if default_language is not None:
            self.default_language = default_language
        if status is not None and status != ProjectStatus.ARCHIVED:
            self.status = status
        self.updated_at = utc_now()

    def archive(self) -> None:
        self.status = ProjectStatus.ARCHIVED
        self.archived_at = utc_now()
        self.updated_at = utc_now()

    def ensure_active_for_knowledge_spaces(self) -> None:
        if self.status == ProjectStatus.ARCHIVED:
            raise InvalidResourceStateError(
                "Archived projects cannot receive new knowledge spaces."
            )
