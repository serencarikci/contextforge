"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from contextforge.application.ports.embedding_provider import EmbeddingProviderPort
from contextforge.application.ports.ingestion_job_queue import IngestionJobQueuePort
from contextforge.application.ports.lexical_search import LexicalSearchPort
from contextforge.application.ports.llm_provider import LlmProviderPort
from contextforge.application.ports.reranker import RerankerPort
from contextforge.application.ports.vector_store import VectorStorePort
from contextforge.application.services.health_service import HealthService
from contextforge.application.services.system_info_service import SystemInfoService
from contextforge.infrastructure.cache.redis_client import RedisClient
from contextforge.infrastructure.database.session import DatabaseManager
from contextforge.infrastructure.embeddings import build_embedding_provider
from contextforge.infrastructure.llm import build_llm_provider
from contextforge.infrastructure.object_storage.minio_client import MinioClient
from contextforge.infrastructure.queue.ingestion_job_queue import (
    InMemoryIngestionJobQueue,
    RedisIngestionJobQueue,
)
from contextforge.infrastructure.reranking import build_reranker
from contextforge.infrastructure.retrieval import InMemoryLexicalSearch, PostgresBm25LexicalSearch
from contextforge.infrastructure.vector_store.qdrant_client import QdrantHealthClient
from contextforge.infrastructure.vector_store.qdrant_vector_store import QdrantVectorStore
from contextforge.modules.documents.application.ports.document_chunker import DocumentChunkerPort
from contextforge.modules.documents.application.ports.document_parser import DocumentParserPort
from contextforge.modules.documents.application.services.document_embedding_service import (
    DocumentEmbeddingService,
)
from contextforge.modules.documents.infrastructure.chunking.semantic_text_chunker import (
    SemanticTextChunker,
)
from contextforge.modules.documents.infrastructure.parsing.composite_parser import (
    CompositeDocumentParser,
)
from contextforge.modules.ingestion.application.services.ingestion_job_service import (
    IngestionJobService,
)
from contextforge.modules.rag.application.prompts.registry import PromptRegistry
from contextforge.modules.rag.application.services.hybrid_retrieval_service import (
    HybridRetrievalService,
)
from contextforge.modules.rag.application.services.rag_query_service import RagQueryService
from contextforge.shared.config.settings import Environment, Settings


def get_settings_dependency(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]


def get_database(request: Request) -> DatabaseManager:
    return request.app.state.database  # type: ignore[no-any-return]


def get_minio_client(request: Request) -> MinioClient:
    return request.app.state.minio_client  # type: ignore[no-any-return]


def get_document_parser() -> DocumentParserPort:
    return CompositeDocumentParser()


def get_document_chunker() -> DocumentChunkerPort:
    return SemanticTextChunker()


def get_vector_store(request: Request) -> VectorStorePort:
    existing = getattr(request.app.state, "vector_store", None)
    if existing is not None:
        return existing  # type: ignore[no-any-return]
    settings: Settings = request.app.state.settings
    store = QdrantVectorStore(settings.qdrant)
    request.app.state.vector_store = store
    return store


def get_embedding_provider(request: Request) -> EmbeddingProviderPort:
    existing = getattr(request.app.state, "embedding_provider", None)
    if existing is not None:
        return existing  # type: ignore[no-any-return]
    settings: Settings = request.app.state.settings
    provider = build_embedding_provider(settings.embedding)
    request.app.state.embedding_provider = provider
    return provider


def get_document_embedding_service(
    request: Request,
    provider: Annotated[EmbeddingProviderPort, Depends(get_embedding_provider)],
    vector_store: Annotated[VectorStorePort, Depends(get_vector_store)],
) -> DocumentEmbeddingService:
    settings: Settings = request.app.state.settings
    return DocumentEmbeddingService(
        provider,
        vector_store,
        batch_size=settings.embedding.batch_size,
        max_retries=settings.embedding.max_retries,
        retry_backoff_seconds=settings.embedding.retry_backoff_seconds,
    )


def get_ingestion_job_queue(request: Request) -> IngestionJobQueuePort:
    existing = getattr(request.app.state, "ingestion_job_queue", None)
    if existing is not None:
        return existing  # type: ignore[no-any-return]
    settings: Settings = request.app.state.settings
    if settings.app.environment == Environment.TEST:
        queue: IngestionJobQueuePort = InMemoryIngestionJobQueue()
    else:
        redis_client: RedisClient = request.app.state.redis_client
        queue = RedisIngestionJobQueue(redis_client.client, settings.ingestion)
    request.app.state.ingestion_job_queue = queue
    return queue


def get_ingestion_job_service(request: Request) -> IngestionJobService:
    settings: Settings = request.app.state.settings
    return IngestionJobService(settings.ingestion)


def get_lexical_search(request: Request) -> LexicalSearchPort:
    existing = getattr(request.app.state, "lexical_search", None)
    if existing is not None:
        return existing  # type: ignore[no-any-return]
    settings: Settings = request.app.state.settings
    if settings.app.environment == Environment.TEST:
        search: LexicalSearchPort = InMemoryLexicalSearch()
    else:
        database: DatabaseManager = request.app.state.database
        search = PostgresBm25LexicalSearch(database.session_factory)
    request.app.state.lexical_search = search
    return search


def get_reranker(request: Request) -> RerankerPort:
    existing = getattr(request.app.state, "reranker", None)
    if existing is not None:
        return existing  # type: ignore[no-any-return]
    settings: Settings = request.app.state.settings
    reranker = build_reranker(settings.rerank)
    request.app.state.reranker = reranker
    return reranker


def get_llm_provider(request: Request) -> LlmProviderPort:
    existing = getattr(request.app.state, "llm_provider", None)
    if existing is not None:
        return existing  # type: ignore[no-any-return]
    settings: Settings = request.app.state.settings
    provider = build_llm_provider(settings.llm)
    request.app.state.llm_provider = provider
    return provider


def get_prompt_registry(request: Request) -> PromptRegistry:
    existing = getattr(request.app.state, "prompt_registry", None)
    if existing is not None:
        return existing  # type: ignore[no-any-return]
    settings: Settings = request.app.state.settings
    registry = PromptRegistry(settings.prompts)
    request.app.state.prompt_registry = registry
    return registry


def get_hybrid_retrieval_service(
    request: Request,
    embedding_provider: Annotated[EmbeddingProviderPort, Depends(get_embedding_provider)],
    vector_store: Annotated[VectorStorePort, Depends(get_vector_store)],
    lexical_search: Annotated[LexicalSearchPort, Depends(get_lexical_search)],
) -> HybridRetrievalService:
    settings: Settings = request.app.state.settings
    database: DatabaseManager = request.app.state.database
    return HybridRetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        lexical_search=lexical_search,
        session_factory=database.session_factory,
        settings=settings.rag,
    )


def get_rag_query_service(
    request: Request,
    retrieval: Annotated[HybridRetrievalService, Depends(get_hybrid_retrieval_service)],
    reranker: Annotated[RerankerPort, Depends(get_reranker)],
    llm: Annotated[LlmProviderPort, Depends(get_llm_provider)],
    prompts: Annotated[PromptRegistry, Depends(get_prompt_registry)],
) -> RagQueryService:
    settings: Settings = request.app.state.settings
    return RagQueryService(
        retrieval=retrieval,
        reranker=reranker,
        llm=llm,
        prompts=prompts,
        rag_settings=settings.rag,
        rerank_settings=settings.rerank,
    )


def get_health_service(request: Request) -> HealthService:
    database: DatabaseManager = request.app.state.database
    redis_client: RedisClient = request.app.state.redis_client
    qdrant_client: QdrantHealthClient = request.app.state.qdrant_client
    minio_client: MinioClient = request.app.state.minio_client
    return HealthService(
        checkers=[database, redis_client, qdrant_client, minio_client],
    )


def get_system_info_service(
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> SystemInfoService:
    return SystemInfoService(settings)
