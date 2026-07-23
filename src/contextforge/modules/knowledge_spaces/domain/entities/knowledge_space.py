"""Knowledge space and membership entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from contextforge.domain.exceptions.identity import InvalidResourceStateError
from contextforge.modules.identity_access.domain.enums import (
    KnowledgeSpaceAccessLevel,
    KnowledgeSpaceStatus,
    KnowledgeSpaceVisibility,
)
from contextforge.modules.identity_access.domain.value_objects import KnowledgeSpaceSlug
from contextforge.shared.utilities.datetime import utc_now


@dataclass(slots=True)
class KnowledgeSpace:
    organization_id: UUID
    name: str
    slug: str
    id: UUID = field(default_factory=uuid4)
    project_id: UUID | None = None
    description: str | None = None
    visibility: KnowledgeSpaceVisibility = KnowledgeSpaceVisibility.ORGANIZATION
    status: KnowledgeSpaceStatus = KnowledgeSpaceStatus.ACTIVE
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    archived_at: datetime | None = None

    def __post_init__(self) -> None:
        cleaned = self.name.strip()
        if len(cleaned) < 2 or len(cleaned) > 200:
            msg = "Knowledge space name must be between 2 and 200 characters"
            raise ValueError(msg)
        self.name = cleaned
        self.slug = KnowledgeSpaceSlug(self.slug).value

    def update(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        visibility: KnowledgeSpaceVisibility | None = None,
    ) -> None:
        if self.status == KnowledgeSpaceStatus.ARCHIVED:
            raise InvalidResourceStateError("Archived knowledge spaces cannot be updated.")
        if name is not None:
            cleaned = name.strip()
            if len(cleaned) < 2 or len(cleaned) > 200:
                msg = "Knowledge space name must be between 2 and 200 characters"
                raise ValueError(msg)
            self.name = cleaned
        if description is not None:
            self.description = description
        if visibility is not None:
            self.visibility = visibility
        self.updated_at = utc_now()

    def archive(self) -> None:
        self.status = KnowledgeSpaceStatus.ARCHIVED
        self.archived_at = utc_now()
        self.updated_at = utc_now()


@dataclass(slots=True)
class KnowledgeSpaceMembership:
    organization_id: UUID
    knowledge_space_id: UUID
    membership_id: UUID
    access_level: KnowledgeSpaceAccessLevel
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def update_access_level(self, access_level: KnowledgeSpaceAccessLevel) -> None:
        self.access_level = access_level
        self.updated_at = utc_now()
