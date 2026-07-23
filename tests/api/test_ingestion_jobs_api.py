"""API tests for automatic ingestion job enqueue and retry."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from contextforge.application.ports.vector_store import ChunkVectorPoint
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.bootstrap.app_factory import create_app
from contextforge.infrastructure.embeddings import build_embedding_provider
from contextforge.infrastructure.queue.ingestion_job_queue import InMemoryIngestionJobQueue
from contextforge.modules.documents.application.services.document_embedding_service import (
    DocumentEmbeddingService,
)
from contextforge.modules.documents.infrastructure.chunking.semantic_text_chunker import (
    SemanticTextChunker,
)
from contextforge.modules.documents.infrastructure.parsing.composite_parser import (
    CompositeDocumentParser,
)
from contextforge.modules.ingestion.application.services.ingestion_pipeline_runner import (
    IngestionPipelineRunner,
)
from contextforge.modules.ingestion.domain.enums import IngestionJobStatus, IngestionJobStep
from contextforge.shared.config.settings import Settings, clear_settings_cache

if TYPE_CHECKING:
    from tests.conftest import TenantScenario


class _FakeVectorStore:
    def __init__(self) -> None:
        self.upserted: list[ChunkVectorPoint] = []

    async def upsert_chunk_vectors(self, points: list[ChunkVectorPoint]) -> None:
        self.upserted.extend(points)

    async def delete_by_document(self, organization_id: object, document_id: object) -> None:
        return None

    async def ensure_ready(self, *, dimensions: int) -> None:
        return None


def _create_knowledge_space(api_client: TestClient, headers: dict[str, str]) -> str:
    response = api_client.post(
        "/api/v1/knowledge-spaces",
        json={"name": "Ingest KS", "slug": f"ingest-ks-{uuid4().hex[:10]}"},
        headers=headers,
    )
    assert response.status_code == 201
    return str(response.json()["id"])


async def _acreate_knowledge_space(client: httpx.AsyncClient, headers: dict[str, str]) -> str:
    response = await client.post(
        "/api/v1/knowledge-spaces",
        json={"name": "Ingest KS", "slug": f"ingest-ks-{uuid4().hex[:10]}"},
        headers=headers,
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def _build_runner(
    *,
    settings: Settings,
    app: object,
    queue: InMemoryIngestionJobQueue,
    vector_store: _FakeVectorStore,
) -> IngestionPipelineRunner:
    provider = build_embedding_provider(settings.embedding)
    return IngestionPipelineRunner(
        settings=settings,
        session_factory=app.state.database.session_factory,  # type: ignore[attr-defined]
        queue=queue,
        storage=app.state.minio_client,  # type: ignore[attr-defined]
        parser=CompositeDocumentParser(),
        chunker=SemanticTextChunker(),
        embedding_service=DocumentEmbeddingService(
            provider,
            vector_store,  # type: ignore[arg-type]
            batch_size=settings.embedding.batch_size,
            max_retries=settings.embedding.max_retries,
            retry_backoff_seconds=settings.embedding.retry_backoff_seconds,
        ),
        vector_store=vector_store,  # type: ignore[arg-type]
        ingestion_settings=settings.ingestion,
    )


@pytest.mark.api
def test_upload_enqueues_ingestion_job(
    integration_settings: Settings, tenant_scenario: TenantScenario
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    queue = InMemoryIngestionJobQueue()
    app.state.ingestion_job_queue = queue

    with TestClient(app) as api_client:
        headers = tenant_scenario.admin_headers()
        ks_id = _create_knowledge_space(api_client, headers)
        upload = api_client.post(
            "/api/v1/documents",
            data={"knowledge_space_id": ks_id, "title": "Queued Doc"},
            files={"file": ("note.md", b"# Title\n\nBody text for parsing.", "text/markdown")},
            headers=headers,
        )
        assert upload.status_code == 201
        document_id = upload.json()["id"]

        assert len(queue.pending) == 1

        listed = api_client.get(
            f"/api/v1/documents/{document_id}/ingestion-jobs",
            headers=headers,
        )
        assert listed.status_code == 200
        items = listed.json()["items"]
        assert len(items) == 1
        assert items[0]["status"] == IngestionJobStatus.PENDING.value
        assert items[0]["document_id"] == document_id
        assert items[0]["id"] == str(queue.pending[0])

        org_listed = api_client.get("/api/v1/ingestion-jobs", headers=headers)
        assert org_listed.status_code == 200
        assert org_listed.json()["pagination"]["total"] >= 1


@pytest.mark.api
@pytest.mark.asyncio
async def test_worker_pipeline_succeeds_for_uploaded_markdown(
    integration_settings: Settings, tenant_scenario: TenantScenario
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    queue = InMemoryIngestionJobQueue()
    fake_store = _FakeVectorStore()

    async with app.router.lifespan_context(app):
        app.state.ingestion_job_queue = queue
        app.state.vector_store = fake_store
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            headers = tenant_scenario.admin_headers()
            ks_id = await _acreate_knowledge_space(client, headers)
            body = "# Overview\n\n" + " ".join(f"token{i}" for i in range(80))
            upload = await client.post(
                "/api/v1/documents",
                data={"knowledge_space_id": ks_id, "title": "Pipeline Doc"},
                files={"file": ("guide.md", body.encode("utf-8"), "text/markdown")},
                headers=headers,
            )
            assert upload.status_code == 201
            document_id = upload.json()["id"]
            job_id = queue.pending[0]

            runner = _build_runner(
                settings=integration_settings,
                app=app,
                queue=queue,
                vector_store=fake_store,
            )
            await runner.process_job(job_id)

            job_response = await client.get(f"/api/v1/ingestion-jobs/{job_id}", headers=headers)
            assert job_response.status_code == 200
            payload = job_response.json()
            assert payload["status"] == IngestionJobStatus.SUCCEEDED.value
            assert payload["document_id"] == document_id
            assert payload["current_step"] == "done"
            assert len(fake_store.upserted) >= 1


@pytest.mark.api
@pytest.mark.asyncio
async def test_retry_failed_job_requeues(
    integration_settings: Settings, tenant_scenario: TenantScenario
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    queue = InMemoryIngestionJobQueue()

    async with app.router.lifespan_context(app):
        app.state.ingestion_job_queue = queue
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            headers = tenant_scenario.admin_headers()
            ks_id = await _acreate_knowledge_space(client, headers)
            upload = await client.post(
                "/api/v1/documents",
                data={"knowledge_space_id": ks_id, "title": "Retry Doc"},
                files={"file": ("a.md", b"# Hi\n\nBody", "text/markdown")},
                headers=headers,
            )
            assert upload.status_code == 201
            job_id = await queue.dequeue(timeout_seconds=1)
            assert job_id is not None
            assert queue.pending == []

            uow = SqlAlchemyUnitOfWork(app.state.database.session_factory)
            async with uow:
                job = await uow.ingestion_jobs.get_by_id(job_id)
                assert job is not None
                job.mark_running(IngestionJobStep.PARSE)
                job.register_attempt_failure(error_code="TEST", error_message="forced failure")
                job.mark_failed()
                await uow.ingestion_jobs.update(job)

            retry = await client.post(f"/api/v1/ingestion-jobs/{job_id}/retry", headers=headers)
            assert retry.status_code == 200
            assert retry.json()["status"] == IngestionJobStatus.PENDING.value
            assert retry.json()["attempt_count"] == 0
            assert queue.pending == [job_id]

            bad = await client.post(f"/api/v1/ingestion-jobs/{job_id}/retry", headers=headers)
            assert bad.status_code == 400
