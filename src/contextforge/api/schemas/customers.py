"""Customer request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from contextforge.modules.identity_access.domain.enums import CustomerStatus


class CustomerCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=1, max_length=50)
    description: str | None = None


class CustomerUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    code: str
    description: str | None
    status: CustomerStatus
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


__all__ = ["CustomerCreateRequest", "CustomerResponse", "CustomerUpdateRequest"]
