"""Repository port for audit event persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from contextforge.modules.audit.domain.entities.audit_event import AuditEvent


class AuditEventRepository(Protocol):
    """Port for persisting and loading append-only AuditEvent records."""

    async def add(self, entity: AuditEvent) -> AuditEvent:
        """Persist a new audit event and return the persisted entity."""
        ...

    async def list(
        self,
        organization_id: UUID,
        *,
        limit: int,
        offset: int,
        action: str | None = None,
        resource_type: str | None = None,
        actor_user_id: UUID | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> tuple[list[AuditEvent], int]:
        """Return a page of audit events for the organization, plus total count."""
        ...
