"""Unit tests for ingestion job domain entity."""

from __future__ import annotations

from uuid import uuid4

import pytest

from contextforge.modules.ingestion.domain.entities.ingestion_job import IngestionJob
from contextforge.modules.ingestion.domain.enums import IngestionJobStatus, IngestionJobStep


@pytest.mark.unit
def test_ingestion_job_lifecycle_and_retry_limits() -> None:
    job = IngestionJob.create(
        organization_id=uuid4(),
        document_id=uuid4(),
        knowledge_space_id=uuid4(),
        requested_by_user_id=uuid4(),
        max_attempts=2,
    )
    assert job.status is IngestionJobStatus.PENDING
    assert job.current_step is IngestionJobStep.QUEUED

    job.mark_running(IngestionJobStep.PARSE)
    assert job.status is IngestionJobStatus.RUNNING
    assert job.started_at is not None

    job.register_attempt_failure(error_code="X", error_message="boom")
    assert job.attempt_count == 1
    assert job.can_retry is True
    job.requeue_for_retry()
    assert job.status is IngestionJobStatus.PENDING

    job.register_attempt_failure(error_code="X", error_message="boom again")
    assert job.can_retry is False
    job.mark_failed()
    assert job.status is IngestionJobStatus.FAILED
    assert job.finished_at is not None

    job.reset_for_manual_retry()
    assert job.status is IngestionJobStatus.PENDING
    assert job.attempt_count == 0
    assert job.last_error is None


@pytest.mark.unit
def test_ingestion_job_mark_succeeded_clears_errors() -> None:
    job = IngestionJob.create(
        organization_id=uuid4(),
        document_id=uuid4(),
        knowledge_space_id=uuid4(),
        requested_by_user_id=uuid4(),
    )
    job.register_attempt_failure(error_code="E", error_message="temporary")
    job.mark_running(IngestionJobStep.EMBED)
    job.mark_succeeded()
    assert job.status is IngestionJobStatus.SUCCEEDED
    assert job.current_step is IngestionJobStep.DONE
    assert job.last_error is None
    assert job.error_code is None
