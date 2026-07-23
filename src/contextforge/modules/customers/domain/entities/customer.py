"""Customer entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from contextforge.domain.exceptions.identity import InvalidResourceStateError
from contextforge.modules.identity_access.domain.enums import CustomerStatus
from contextforge.modules.identity_access.domain.value_objects import CustomerCode
from contextforge.shared.utilities.datetime import utc_now


@dataclass(slots=True)
class Customer:
    organization_id: UUID
    name: str
    code: str
    id: UUID = field(default_factory=uuid4)
    description: str | None = None
    status: CustomerStatus = CustomerStatus.ACTIVE
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    archived_at: datetime | None = None

    def __post_init__(self) -> None:
        self.name = self._validate_name(self.name)
        self.code = CustomerCode(self.code).value

    @staticmethod
    def _validate_name(name: str) -> str:
        cleaned = name.strip()
        if len(cleaned) < 2 or len(cleaned) > 200:
            msg = "Customer name must be between 2 and 200 characters"
            raise ValueError(msg)
        return cleaned

    def update(self, *, name: str | None = None, description: str | None = None) -> None:
        if self.status == CustomerStatus.ARCHIVED:
            raise InvalidResourceStateError("Archived customers cannot be updated.")
        if name is not None:
            self.name = self._validate_name(name)
        if description is not None:
            self.description = description
        self.updated_at = utc_now()

    def archive(self) -> None:
        self.status = CustomerStatus.ARCHIVED
        self.archived_at = utc_now()
        self.updated_at = utc_now()

    def ensure_active_for_projects(self) -> None:
        if self.status == CustomerStatus.ARCHIVED:
            raise InvalidResourceStateError("Archived customers cannot receive new projects.")
