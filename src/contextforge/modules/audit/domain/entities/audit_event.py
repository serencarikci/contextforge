"""Append-only audit event entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from contextforge.shared.utilities.datetime import utc_now

_FORBIDDEN_METADATA_KEYS = {
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "api_key",
    "access_key",
    "secret_key",
}


@dataclass(slots=True)
class AuditEvent:
    action: str
    resource_type: str
    id: UUID = field(default_factory=uuid4)
    organization_id: UUID | None = None
    actor_user_id: UUID | None = None
    resource_id: UUID | None = None
    correlation_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.action = self.action.strip()
        self.resource_type = self.resource_type.strip()
        if not self.action or not self.resource_type:
            msg = "Audit action and resource_type are required"
            raise ValueError(msg)
        self.metadata = self.sanitize_metadata(self.metadata)

    @staticmethod
    def sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        for key, value in metadata.items():
            lowered = key.lower()
            if any(part in lowered for part in _FORBIDDEN_METADATA_KEYS):
                continue
            sanitized[key] = value
        return sanitized
