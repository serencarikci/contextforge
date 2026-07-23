"""Organization request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from contextforge.modules.identity_access.domain.enums import OrganizationStatus


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    slug: str = Field(min_length=1, max_length=100)


class OrganizationUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    status: OrganizationStatus
    created_at: datetime
    updated_at: datetime


__all__ = ["OrganizationCreateRequest", "OrganizationResponse", "OrganizationUpdateRequest"]
