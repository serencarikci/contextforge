"""Document request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from contextforge.modules.documents.domain.enums import DocumentStatus


class DocumentMetadataUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    knowledge_space_id: UUID
    title: str
    filename: str
    content_type: str
    size_bytes: int
    checksum_sha256: str | None
    status: DocumentStatus
    uploaded_by_user_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


__all__ = ["DocumentMetadataUpdateRequest", "DocumentResponse"]
