"""Audit event response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID | None
    actor_user_id: UUID | None
    action: str
    resource_type: str
    resource_id: UUID | None
    correlation_id: UUID | None
    metadata: dict[str, Any]
    occurred_at: datetime


__all__ = ["AuditEventResponse"]
