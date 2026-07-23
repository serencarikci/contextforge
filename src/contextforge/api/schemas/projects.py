"""Project request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from contextforge.modules.identity_access.domain.enums import PreferredLanguage, ProjectStatus


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    key: str = Field(min_length=1, max_length=50)
    customer_id: UUID | None = None
    description: str | None = None
    default_language: PreferredLanguage | None = None


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    default_language: PreferredLanguage | None = None
    status: ProjectStatus | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    key: str
    customer_id: UUID | None
    description: str | None
    status: ProjectStatus
    default_language: PreferredLanguage
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


__all__ = ["ProjectCreateRequest", "ProjectResponse", "ProjectUpdateRequest"]
