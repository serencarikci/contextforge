"""Role and role assignment request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RoleCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None


class RoleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    organization_id: UUID | None
    description: str | None
    is_system: bool
    created_at: datetime
    updated_at: datetime


class RoleAssignmentCreateRequest(BaseModel):
    membership_id: UUID
    role_id: UUID
    project_id: UUID | None = None
    knowledge_space_id: UUID | None = None


class RoleAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    membership_id: UUID
    role_id: UUID
    project_id: UUID | None
    knowledge_space_id: UUID | None
    created_at: datetime


__all__ = [
    "RoleAssignmentCreateRequest",
    "RoleAssignmentResponse",
    "RoleCreateRequest",
    "RoleResponse",
    "RoleUpdateRequest",
]
