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
from contextforge.modules.admin.application.ports.admin_cache import AdminCachePort
from contextforge.modules.admin.application.ports.llm_connectivity import LlmConnectivityCheckPort
from contextforge.modules.admin.application.ports.secret_cipher import SecretCipherPort
from contextforge.modules.admin.application.services.admin_role_service import AdminRoleService
from contextforge.modules.admin.application.services.admin_user_service import AdminUserService
from contextforge.modules.admin.application.services.audit_export_service import AuditExportService
from contextforge.modules.admin.application.services.dashboard_service import DashboardService
from contextforge.modules.admin.application.services.document_ops_service import DocumentOpsService
from contextforge.modules.admin.application.services.feature_flag_service import FeatureFlagService
from contextforge.modules.admin.application.services.ingestion_ops_service import (
    IngestionOpsService,
)
from contextforge.modules.admin.application.services.knowledge_space_admin_service import (
    KnowledgeSpaceAdminService,
)
from contextforge.modules.admin.application.services.llm_config_service import LlmConfigService
from contextforge.modules.admin.application.services.ops_service import OpsService
from contextforge.modules.admin.application.services.organization_settings_service import (
    OrganizationSettingsService,
)
from contextforge.modules.admin.application.services.prompt_admin_service import PromptAdminService
from contextforge.modules.admin.application.services.prompt_override_source import (
    DatabasePromptOverrideSource,
)
from contextforge.modules.admin.application.services.retention_service import (
    RetentionCleanupService,
)
from contextforge.modules.admin.application.services.token_usage_service import TokenUsageService
from contextforge.modules.admin.application.services.usage_analytics_service import (
    UsageAnalyticsService,
)
from contextforge.modules.admin.infrastructure.cache import InMemoryAdminCache, RedisAdminCache
from contextforge.modules.admin.infrastructure.crypto import FernetSecretCipher
from contextforge.modules.admin.infrastructure.llm import HttpLlmConnectivityChecker
from contextforge.modules.chat.application.ports.cancellation import StreamCancellationPort
from contextforge.modules.chat.application.services.analytics_service import AnalyticsService
from contextforge.modules.chat.application.services.chat_service import ChatService
from contextforge.modules.chat.application.services.conversation_search_service import (
    ConversationSearchService,
)
from contextforge.modules.chat.application.services.conversation_service import (
    ConversationService,
)
from contextforge.modules.chat.application.services.export_service import ExportService
from contextforge.modules.chat.application.services.feedback_service import FeedbackService
from contextforge.modules.chat.application.services.language_service import LanguageService
from contextforge.modules.chat.application.services.memory_service import MemoryService
from contextforge.modules.chat.application.services.suggestion_service import SuggestionService
from contextforge.modules.chat.infrastructure.cancellation import (
    InMemoryStreamCancellationRegistry,
)
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
    registry = PromptRegistry(
        settings.prompts,
        override_source=DatabasePromptOverrideSource(),
    )
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


def get_token_usage_service(request: Request) -> TokenUsageService:
    settings: Settings = request.app.state.settings
    return TokenUsageService(settings.admin)


def get_rag_query_service(
    request: Request,
    retrieval: Annotated[HybridRetrievalService, Depends(get_hybrid_retrieval_service)],
    reranker: Annotated[RerankerPort, Depends(get_reranker)],
    llm: Annotated[LlmProviderPort, Depends(get_llm_provider)],
    prompts: Annotated[PromptRegistry, Depends(get_prompt_registry)],
    token_usage: Annotated[TokenUsageService, Depends(get_token_usage_service)],
) -> RagQueryService:
    settings: Settings = request.app.state.settings
    return RagQueryService(
        retrieval=retrieval,
        reranker=reranker,
        llm=llm,
        prompts=prompts,
        rag_settings=settings.rag,
        rerank_settings=settings.rerank,
        token_usage=token_usage,
        llm_provider_name=settings.llm.provider,
    )


def get_chat_cancellation_registry(request: Request) -> StreamCancellationPort:
    existing = getattr(request.app.state, "chat_cancellation_registry", None)
    if existing is not None:
        return existing  # type: ignore[no-any-return]
    registry = InMemoryStreamCancellationRegistry()
    request.app.state.chat_cancellation_registry = registry
    return registry


def get_language_service(request: Request) -> LanguageService:
    settings: Settings = request.app.state.settings
    return LanguageService(settings.chat)


def get_memory_service(request: Request) -> MemoryService:
    settings: Settings = request.app.state.settings
    return MemoryService(settings.chat)


def get_conversation_service(request: Request) -> ConversationService:
    settings: Settings = request.app.state.settings
    return ConversationService(settings.chat)


def get_admin_cache(request: Request) -> AdminCachePort:
    existing = getattr(request.app.state, "admin_cache", None)
    if existing is not None:
        return existing  # type: ignore[no-any-return]
    settings: Settings = request.app.state.settings
    if settings.app.environment == Environment.TEST:
        cache: AdminCachePort = InMemoryAdminCache()
    else:
        redis_client: RedisClient = request.app.state.redis_client
        cache = RedisAdminCache(redis_client.client)
    request.app.state.admin_cache = cache
    return cache


def get_secret_cipher(request: Request) -> SecretCipherPort:
    existing = getattr(request.app.state, "secret_cipher", None)
    if existing is not None:
        return existing  # type: ignore[no-any-return]
    settings: Settings = request.app.state.settings
    cipher: SecretCipherPort = FernetSecretCipher(settings.security.secret_key.get_secret_value())
    request.app.state.secret_cipher = cipher
    return cipher


def get_llm_connectivity_checker(request: Request) -> LlmConnectivityCheckPort:
    existing = getattr(request.app.state, "llm_connectivity_checker", None)
    if existing is not None:
        return existing  # type: ignore[no-any-return]
    checker: LlmConnectivityCheckPort = HttpLlmConnectivityChecker()
    request.app.state.llm_connectivity_checker = checker
    return checker


def get_feature_flag_service(
    request: Request,
    cache: Annotated[AdminCachePort, Depends(get_admin_cache)],
) -> FeatureFlagService:
    settings: Settings = request.app.state.settings
    return FeatureFlagService(cache, settings.admin)


def get_llm_config_service(
    request: Request,
    cipher: Annotated[SecretCipherPort, Depends(get_secret_cipher)],
    connectivity: Annotated[LlmConnectivityCheckPort, Depends(get_llm_connectivity_checker)],
) -> LlmConfigService:
    settings: Settings = request.app.state.settings
    return LlmConfigService(cipher, connectivity, settings.admin)


def get_document_ops_service(request: Request) -> DocumentOpsService:
    settings: Settings = request.app.state.settings
    return DocumentOpsService(settings.ingestion)


def get_retention_cleanup_service(request: Request) -> RetentionCleanupService:
    settings: Settings = request.app.state.settings
    return RetentionCleanupService(settings.admin)


def get_health_service(request: Request) -> HealthService:
    database: DatabaseManager = request.app.state.database
    redis_client: RedisClient = request.app.state.redis_client
    qdrant_client: QdrantHealthClient = request.app.state.qdrant_client
    minio_client: MinioClient = request.app.state.minio_client
    return HealthService(
        checkers=[database, redis_client, qdrant_client, minio_client],
    )


def get_ops_service(
    request: Request,
    health: Annotated[HealthService, Depends(get_health_service)],
) -> OpsService:
    settings: Settings = request.app.state.settings
    return OpsService(health, settings)


def get_chat_service(
    request: Request,
    rag_query_service: Annotated[RagQueryService, Depends(get_rag_query_service)],
    memory_service: Annotated[MemoryService, Depends(get_memory_service)],
    language_service: Annotated[LanguageService, Depends(get_language_service)],
    cancellation: Annotated[StreamCancellationPort, Depends(get_chat_cancellation_registry)],
    token_usage: Annotated[TokenUsageService, Depends(get_token_usage_service)],
) -> ChatService:
    settings: Settings = request.app.state.settings
    return ChatService(
        rag_query_service=rag_query_service,
        memory_service=memory_service,
        language_service=language_service,
        cancellation=cancellation,
        chat_settings=settings.chat,
        rag_settings=settings.rag,
        token_usage=token_usage,
        llm_provider_name=settings.llm.provider,
    )


def get_feedback_service() -> FeedbackService:
    return FeedbackService()


def get_conversation_search_service() -> ConversationSearchService:
    return ConversationSearchService()


def get_suggestion_service(request: Request) -> SuggestionService:
    settings: Settings = request.app.state.settings
    return SuggestionService(settings.chat)


def get_export_service(request: Request) -> ExportService:
    settings: Settings = request.app.state.settings
    return ExportService(settings.chat)


def get_chat_analytics_service() -> AnalyticsService:
    return AnalyticsService()


def get_system_info_service(
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> SystemInfoService:
    return SystemInfoService(settings)


def get_dashboard_service() -> DashboardService:
    return DashboardService()


def get_admin_user_service() -> AdminUserService:
    return AdminUserService()


def get_admin_role_service() -> AdminRoleService:
    return AdminRoleService()


def get_organization_settings_service() -> OrganizationSettingsService:
    return OrganizationSettingsService()


def get_knowledge_space_admin_service() -> KnowledgeSpaceAdminService:
    return KnowledgeSpaceAdminService()


def get_ingestion_ops_service() -> IngestionOpsService:
    return IngestionOpsService()


def get_audit_export_service() -> AuditExportService:
    return AuditExportService()


def get_usage_analytics_service() -> UsageAnalyticsService:
    return UsageAnalyticsService()


def get_prompt_admin_service() -> PromptAdminService:
    return PromptAdminService()


def get_retention_service(request: Request) -> RetentionCleanupService:
    return get_retention_cleanup_service(request)
