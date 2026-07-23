"""Ingestion job entity for background document processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from contextforge.modules.ingestion.domain.enums import IngestionJobStatus, IngestionJobStep
from contextforge.shared.utilities.datetime import utc_now


@dataclass(slots=True)
class IngestionJob:
    """Durable background job that drives parse -> chunk -> embed."""

    organization_id: UUID
    document_id: UUID
    knowledge_space_id: UUID
    requested_by_user_id: UUID
    id: UUID = field(default_factory=uuid4)
    status: IngestionJobStatus = IngestionJobStatus.PENDING
    current_step: IngestionJobStep = IngestionJobStep.QUEUED
    attempt_count: int = 0
    max_attempts: int = 3
    last_error: str | None = None
    error_code: str | None = None
    queued_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        document_id: UUID,
        knowledge_space_id: UUID,
        requested_by_user_id: UUID,
        max_attempts: int = 3,
    ) -> IngestionJob:
        return cls(
            organization_id=organization_id,
            document_id=document_id,
            knowledge_space_id=knowledge_space_id,
            requested_by_user_id=requested_by_user_id,
            max_attempts=max_attempts,
        )

    @property
    def can_retry(self) -> bool:
        return self.attempt_count < self.max_attempts

    def mark_running(self, step: IngestionJobStep) -> None:
        self.status = IngestionJobStatus.RUNNING
        self.current_step = step
        if self.started_at is None:
            self.started_at = utc_now()
        self.updated_at = utc_now()

    def advance_step(self, step: IngestionJobStep) -> None:
        self.current_step = step
        self.updated_at = utc_now()

    def mark_succeeded(self) -> None:
        self.status = IngestionJobStatus.SUCCEEDED
        self.current_step = IngestionJobStep.DONE
        self.last_error = None
        self.error_code = None
        self.finished_at = utc_now()
        self.updated_at = utc_now()

    def register_attempt_failure(self, *, error_code: str, error_message: str) -> None:
        self.attempt_count += 1
        self.error_code = error_code
        self.last_error = error_message[:4000]
        self.updated_at = utc_now()

    def mark_failed(self) -> None:
        self.status = IngestionJobStatus.FAILED
        self.finished_at = utc_now()
        self.updated_at = utc_now()

    def requeue_for_retry(self) -> None:
        self.status = IngestionJobStatus.PENDING
        self.current_step = IngestionJobStep.QUEUED
        self.started_at = None
        self.finished_at = None
        self.queued_at = utc_now()
        self.updated_at = utc_now()

    def reset_for_manual_retry(self) -> None:
        self.status = IngestionJobStatus.PENDING
        self.current_step = IngestionJobStep.QUEUED
        self.attempt_count = 0
        self.last_error = None
        self.error_code = None
        self.started_at = None
        self.finished_at = None
        self.queued_at = utc_now()
        self.updated_at = utc_now()


__all__ = ["IngestionJob"]
