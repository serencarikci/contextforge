"""Organization membership entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from contextforge.domain.exceptions.identity import InvalidResourceStateError
from contextforge.modules.identity_access.domain.enums import MembershipStatus
from contextforge.shared.utilities.datetime import utc_now


@dataclass(slots=True)
class OrganizationMembership:
    organization_id: UUID
    user_id: UUID
    id: UUID = field(default_factory=uuid4)
    status: MembershipStatus = MembershipStatus.ACTIVE
    joined_at: datetime = field(default_factory=utc_now)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def suspend(self) -> None:
        if self.status == MembershipStatus.REMOVED:
            raise InvalidResourceStateError("Removed memberships cannot be suspended.")
        self.status = MembershipStatus.SUSPENDED
        self.updated_at = utc_now()

    def remove(self) -> None:
        self.status = MembershipStatus.REMOVED
        self.updated_at = utc_now()

    def ensure_active(self) -> None:
        if self.status != MembershipStatus.ACTIVE:
            raise InvalidResourceStateError("Membership is not active.")
