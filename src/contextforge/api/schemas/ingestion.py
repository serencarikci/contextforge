"""Ingestion job response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from contextforge.modules.ingestion.domain.enums import IngestionJobStatus, IngestionJobStep


class IngestionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    document_id: UUID
    knowledge_space_id: UUID
    requested_by_user_id: UUID
    status: IngestionJobStatus
    current_step: IngestionJobStep
    attempt_count: int
    max_attempts: int
    last_error: str | None = None
    error_code: str | None = None
    queued_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class IngestionJobListResponse(BaseModel):
    items: list[IngestionJobResponse] = Field(default_factory=list)
