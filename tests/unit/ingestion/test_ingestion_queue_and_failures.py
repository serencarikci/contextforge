"""Unit tests for in-memory ingestion job queue and failure handling."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from contextforge.infrastructure.queue.ingestion_job_queue import InMemoryIngestionJobQueue
from contextforge.modules.ingestion.application.services.ingestion_pipeline_runner import (
    IngestionPipelineRunner,
)
from contextforge.modules.ingestion.domain.entities.ingestion_job import IngestionJob
from contextforge.modules.ingestion.domain.enums import IngestionJobStatus
from contextforge.modules.ingestion.domain.exceptions import IngestionJobError
from contextforge.shared.config.settings import IngestionSettings, Settings


@pytest.mark.unit
@pytest.mark.asyncio
async def test_in_memory_queue_fifo() -> None:
    queue = InMemoryIngestionJobQueue()
    first, second = uuid4(), uuid4()
    await queue.enqueue(first)
    await queue.enqueue(second)
    assert await queue.dequeue(timeout_seconds=1) == first
    assert await queue.dequeue(timeout_seconds=1) == second
    assert await queue.dequeue(timeout_seconds=1) is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pipeline_failure_requeues_until_max_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings()
    ingestion = IngestionSettings(max_attempts=2, retry_backoff_seconds=0.01)
    queue = InMemoryIngestionJobQueue()
    job = IngestionJob.create(
        organization_id=uuid4(),
        document_id=uuid4(),
        knowledge_space_id=uuid4(),
        requested_by_user_id=uuid4(),
        max_attempts=2,
    )
    job.mark_running(job.current_step)

    repo = MagicMock()
    repo.get_by_id = AsyncMock(side_effect=[job, job])
    repo.update = AsyncMock(side_effect=lambda entity: entity)

    uow = MagicMock()
    uow.ingestion_jobs = repo
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)

    runner = IngestionPipelineRunner(
        settings=settings,
        session_factory=MagicMock(),
        queue=queue,
        storage=MagicMock(),
        parser=MagicMock(),
        chunker=MagicMock(),
        embedding_service=MagicMock(),
        vector_store=MagicMock(),
        ingestion_settings=ingestion,
    )
    monkeypatch.setattr(runner, "_uow", lambda: uow)

    await runner._handle_failure(job.id, IngestionJobError("parse failed"))
    assert job.status is IngestionJobStatus.PENDING
    assert job.attempt_count == 1
    assert queue.pending == [job.id]

    await queue.dequeue(timeout_seconds=1)
    await runner._handle_failure(job.id, IngestionJobError("parse failed again"))
    assert job.status is IngestionJobStatus.FAILED
    assert job.attempt_count == 2
    assert queue.pending == []
