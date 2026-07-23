"""User request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from contextforge.modules.identity_access.domain.enums import PreferredLanguage, UserStatus


class UserCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=2, max_length=120)
    preferred_language: PreferredLanguage = PreferredLanguage.EN


class UserUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    preferred_language: PreferredLanguage | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str
    status: UserStatus
    preferred_language: PreferredLanguage
    is_platform_admin: bool
    created_at: datetime
    updated_at: datetime


__all__ = ["UserCreateRequest", "UserResponse", "UserUpdateRequest"]
