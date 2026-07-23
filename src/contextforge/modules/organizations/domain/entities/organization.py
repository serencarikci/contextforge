"""Organization aggregate."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from contextforge.domain.exceptions.identity import InvalidResourceStateError
from contextforge.modules.identity_access.domain.enums import OrganizationStatus
from contextforge.modules.identity_access.domain.value_objects import OrganizationSlug
from contextforge.shared.utilities.datetime import utc_now


@dataclass(slots=True)
class Organization:
    name: str
    slug: str
    id: UUID = field(default_factory=uuid4)
    status: OrganizationStatus = OrganizationStatus.ACTIVE
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.name = self._validate_name(self.name)
        self.slug = OrganizationSlug(self.slug).value

    @staticmethod
    def _validate_name(name: str) -> str:
        cleaned = name.strip()
        if len(cleaned) < 2 or len(cleaned) > 150:
            msg = "Organization name must be between 2 and 150 characters"
            raise ValueError(msg)
        return cleaned

    def rename(self, name: str) -> None:
        self._ensure_writable()
        self.name = self._validate_name(name)
        self.updated_at = utc_now()

    def suspend(self) -> None:
        if self.status == OrganizationStatus.ARCHIVED:
            raise InvalidResourceStateError("Archived organizations cannot be suspended.")
        self.status = OrganizationStatus.SUSPENDED
        self.updated_at = utc_now()

    def archive(self) -> None:
        self.status = OrganizationStatus.ARCHIVED
        self.updated_at = utc_now()

    def _ensure_writable(self) -> None:
        if self.status == OrganizationStatus.SUSPENDED:
            raise InvalidResourceStateError(
                "Suspended organizations cannot perform write operations."
            )
        if self.status == OrganizationStatus.ARCHIVED:
            raise InvalidResourceStateError("Archived organizations cannot be modified.")

    def ensure_accepts_memberships(self) -> None:
        if self.status == OrganizationStatus.ARCHIVED:
            raise InvalidResourceStateError(
                "Archived organizations cannot receive new memberships."
            )

    def ensure_writable(self) -> None:
        self._ensure_writable()
