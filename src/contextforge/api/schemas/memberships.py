"""Organization membership request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from contextforge.modules.identity_access.domain.enums import MembershipStatus


class MembershipCreateRequest(BaseModel):
    user_id: UUID


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    user_id: UUID
    status: MembershipStatus
    joined_at: datetime
    created_at: datetime
    updated_at: datetime


__all__ = ["MembershipCreateRequest", "MembershipResponse"]
