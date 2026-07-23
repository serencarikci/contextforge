"""Background worker that drains the document ingestion queue."""

from __future__ import annotations

import asyncio
import signal
from typing import Any

from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.infrastructure.cache.redis_client import RedisClient
from contextforge.infrastructure.database.session import DatabaseManager
from contextforge.infrastructure.embeddings import build_embedding_provider
from contextforge.infrastructure.object_storage.minio_client import MinioClient
from contextforge.infrastructure.queue.ingestion_job_queue import RedisIngestionJobQueue
from contextforge.infrastructure.vector_store.qdrant_vector_store import QdrantVectorStore
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
from contextforge.shared.config.settings import get_settings
from contextforge.shared.logging.setup import configure_logging, get_logger

logger = get_logger(__name__)


class IngestionWorker:
    """Long-running process that claims and executes ingestion jobs."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._stop = asyncio.Event()
        self._database = DatabaseManager(self._settings.postgres)
        self._redis = RedisClient(self._settings.redis)
        self._minio = MinioClient(self._settings.minio)
        self._vector_store = QdrantVectorStore(self._settings.qdrant)
        self._embedding_provider = build_embedding_provider(self._settings.embedding)
        self._queue = RedisIngestionJobQueue(self._redis.client, self._settings.ingestion)
        self._runner = IngestionPipelineRunner(
            settings=self._settings,
            session_factory=self._database.session_factory,
            queue=self._queue,
            storage=self._minio,
            parser=CompositeDocumentParser(),
            chunker=SemanticTextChunker(),
            embedding_service=DocumentEmbeddingService(
                self._embedding_provider,
                self._vector_store,
                batch_size=self._settings.embedding.batch_size,
                max_retries=self._settings.embedding.max_retries,
                retry_backoff_seconds=self._settings.embedding.retry_backoff_seconds,
            ),
            vector_store=self._vector_store,
            ingestion_settings=self._settings.ingestion,
        )

    def request_stop(self, *_args: Any) -> None:
        self._stop.set()

    async def _enqueue_all_pending(self) -> int:
        uow = SqlAlchemyUnitOfWork(self._database.session_factory)
        async with uow:
            pending_ids = await uow.ingestion_jobs.list_pending_ids()
        for job_id in pending_ids:
            await self._queue.enqueue(job_id)
        return len(pending_ids)

    async def run_forever(self) -> None:
        configure_logging(
            self._settings.logging,
            environment=self._settings.app.environment.value,
        )
        recovered = await self._enqueue_all_pending()
        logger.info("ingestion_worker_started", extra={"recovered_pending": recovered})
        idle = self._settings.ingestion.worker_idle_sleep_seconds
        timeout = self._settings.ingestion.poll_timeout_seconds
        try:
            while not self._stop.is_set():
                job_id = await self._queue.dequeue(timeout_seconds=timeout)
                if job_id is None:
                    await asyncio.sleep(idle)
                    continue
                try:
                    await self._runner.process_job(job_id)
                except Exception:
                    logger.exception(
                        "ingestion_worker_unhandled_error",
                        extra={"job_id": str(job_id)},
                    )
        finally:
            await self._shutdown()

    async def _shutdown(self) -> None:
        logger.info("ingestion_worker_stopping")
        await self._minio.close()
        await self._vector_store.close()
        if hasattr(self._embedding_provider, "close"):
            await self._embedding_provider.close()
        await self._redis.close()
        await self._database.dispose()
        logger.info("ingestion_worker_stopped")


def main() -> None:
    worker = IngestionWorker()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, worker.request_stop)
        except NotImplementedError:  # pragma: no cover - Windows
            signal.signal(sig, lambda *_a: worker.request_stop())

    try:
        loop.run_until_complete(worker.run_forever())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
