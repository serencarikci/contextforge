"""User aggregate."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from contextforge.domain.exceptions.identity import InvalidResourceStateError
from contextforge.modules.identity_access.domain.enums import PreferredLanguage, UserStatus
from contextforge.modules.identity_access.domain.value_objects import NormalizedEmail
from contextforge.shared.utilities.datetime import utc_now


@dataclass(slots=True)
class User:
    email: str
    display_name: str
    id: UUID = field(default_factory=uuid4)
    status: UserStatus = UserStatus.ACTIVE
    preferred_language: PreferredLanguage = PreferredLanguage.EN
    is_platform_admin: bool = False
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.email = NormalizedEmail(self.email).value
        self.display_name = self._validate_display_name(self.display_name)

    @staticmethod
    def _validate_display_name(name: str) -> str:
        cleaned = name.strip()
        if len(cleaned) < 2 or len(cleaned) > 120:
            msg = "Display name must be between 2 and 120 characters"
            raise ValueError(msg)
        return cleaned

    def update_profile(
        self,
        *,
        display_name: str | None = None,
        preferred_language: PreferredLanguage | None = None,
    ) -> None:
        self.ensure_active_for_assignment()
        if display_name is not None:
            self.display_name = self._validate_display_name(display_name)
        if preferred_language is not None:
            self.preferred_language = preferred_language
        self.updated_at = utc_now()

    def suspend(self) -> None:
        if self.status == UserStatus.ARCHIVED:
            raise InvalidResourceStateError("Archived users cannot be suspended.")
        self.status = UserStatus.SUSPENDED
        self.updated_at = utc_now()

    def archive(self) -> None:
        self.status = UserStatus.ARCHIVED
        self.updated_at = utc_now()

    def ensure_active_for_actions(self) -> None:
        if self.status != UserStatus.ACTIVE:
            raise InvalidResourceStateError("Only active users can perform protected actions.")

    def ensure_active_for_assignment(self) -> None:
        if self.status == UserStatus.ARCHIVED:
            raise InvalidResourceStateError("Archived users cannot be assigned to organizations.")
