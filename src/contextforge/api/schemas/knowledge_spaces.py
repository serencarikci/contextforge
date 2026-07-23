"""Knowledge space and knowledge space membership request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from contextforge.modules.identity_access.domain.enums import (
    KnowledgeSpaceAccessLevel,
    KnowledgeSpaceStatus,
    KnowledgeSpaceVisibility,
)


class KnowledgeSpaceCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=1, max_length=150)
    project_id: UUID | None = None
    description: str | None = None
    visibility: KnowledgeSpaceVisibility | None = None


class KnowledgeSpaceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    visibility: KnowledgeSpaceVisibility | None = None


class KnowledgeSpaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    project_id: UUID | None
    name: str
    slug: str
    description: str | None
    visibility: KnowledgeSpaceVisibility
    status: KnowledgeSpaceStatus
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class KnowledgeSpaceMembershipCreateRequest(BaseModel):
    membership_id: UUID
    access_level: KnowledgeSpaceAccessLevel


class KnowledgeSpaceMembershipUpdateRequest(BaseModel):
    access_level: KnowledgeSpaceAccessLevel


class KnowledgeSpaceMembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    knowledge_space_id: UUID
    membership_id: UUID
    access_level: KnowledgeSpaceAccessLevel
    created_at: datetime
    updated_at: datetime


__all__ = [
    "KnowledgeSpaceCreateRequest",
    "KnowledgeSpaceMembershipCreateRequest",
    "KnowledgeSpaceMembershipResponse",
    "KnowledgeSpaceMembershipUpdateRequest",
    "KnowledgeSpaceResponse",
    "KnowledgeSpaceUpdateRequest",
]
