"""Typed application settings loaded from environment variables."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Environment(StrEnum):
    """Supported runtime environments."""

    LOCAL = "local"
    TEST = "test"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class AppSettings(BaseSettings):
    """Core application settings."""

    model_config = SettingsConfigDict(extra="ignore")

    name: str = "contextforge-api"
    environment: Environment = Environment.LOCAL
    debug: bool = False
    version: str = "0.5.0"

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value: object) -> object:
        if isinstance(value, str):
            return value.lower()
        return value


class APISettings(BaseSettings):
    """HTTP API settings."""

    model_config = SettingsConfigDict(extra="ignore")

    host: str = "0.0.0.0"  # noqa: S104
    port: int = Field(default=8000, ge=1, le=65535)
    root_path: str = ""
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    docs_enabled: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                import json

                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            return [item.strip() for item in stripped.split(",") if item.strip()]
        msg = "cors_origins must be a list or comma-separated string"
        raise TypeError(msg)


class PostgresSettings(BaseSettings):
    """PostgreSQL connection settings."""

    model_config = SettingsConfigDict(extra="ignore")

    host: str = "localhost"
    port: int = Field(default=5432, ge=1, le=65535)
    user: str = "contextforge"
    password: SecretStr = SecretStr("contextforge_dev_password")
    database: str = "contextforge"
    pool_size: int = Field(default=5, ge=1)
    max_overflow: int = Field(default=10, ge=0)
    echo: bool = False
    connect_timeout_seconds: float = Field(default=5.0, gt=0)

    @property
    def async_dsn(self) -> str:
        password = self.password.get_secret_value()
        return (
            f"postgresql+asyncpg://{self.user}:{password}@{self.host}:{self.port}/{self.database}"
        )


class RedisSettings(BaseSettings):
    """Redis connection settings."""

    model_config = SettingsConfigDict(extra="ignore")

    url: str = "redis://localhost:6379/0"
    timeout_seconds: float = Field(default=2.0, gt=0)


class QdrantSettings(BaseSettings):
    """Qdrant connection settings."""

    model_config = SettingsConfigDict(extra="ignore")

    url: str = "http://localhost:6333"
    api_key: SecretStr | None = None
    timeout_seconds: float = Field(default=3.0, gt=0)
    collection_name: str = "document_chunks"


class EmbeddingSettings(BaseSettings):
    """Embedding generation settings for multilingual chunk vectors."""

    model_config = SettingsConfigDict(extra="ignore")

    provider: Literal["hashing", "openai_compatible"] = "hashing"
    model: str = "contextforge-multilingual-hash-v1"
    dimensions: int = Field(default=384, ge=8, le=4096)
    batch_size: int = Field(default=32, ge=1, le=256)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_backoff_seconds: float = Field(default=0.5, gt=0)
    base_url: str = "https://api.openai.com/v1"
    api_key: SecretStr | None = None
    timeout_seconds: float = Field(default=30.0, gt=0)


class MinioSettings(BaseSettings):
    """MinIO / S3-compatible object storage settings."""

    model_config = SettingsConfigDict(extra="ignore")

    endpoint: str = "localhost:9000"
    access_key: SecretStr = SecretStr("contextforge_minio")
    secret_key: SecretStr = SecretStr("contextforge_minio_secret")
    bucket: str = "contextforge-documents"
    secure: bool = False
    region: str = "us-east-1"
    timeout_seconds: float = Field(default=3.0, gt=0)


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(extra="ignore")

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    format: Literal["json", "console"] = "console"
    service_name: str = "contextforge-api"


class IngestionSettings(BaseSettings):
    """Background document ingestion worker settings."""

    model_config = SettingsConfigDict(extra="ignore")

    enabled: bool = True
    queue_key: str = "contextforge:ingestion:jobs"
    max_attempts: int = Field(default=3, ge=1, le=20)
    poll_timeout_seconds: float = Field(default=5.0, gt=0)
    retry_backoff_seconds: float = Field(default=1.0, gt=0)
    worker_idle_sleep_seconds: float = Field(default=0.5, gt=0)


class RagSettings(BaseSettings):
    """Hybrid retrieval and RAG pipeline settings."""

    model_config = SettingsConfigDict(extra="ignore")

    dense_weight: float = Field(default=0.6, ge=0.0, le=1.0)
    lexical_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    top_k: int = Field(default=20, ge=1, le=100)
    candidate_multiplier: int = Field(default=3, ge=1, le=20)
    max_context_tokens: int = Field(default=3000, ge=128, le=128000)
    max_chunks_in_context: int = Field(default=8, ge=1, le=50)
    default_language: Literal["en", "tr"] = "en"
    fusion_method: Literal["weighted", "rrf"] = "weighted"
    rrf_k: int = Field(default=60, ge=1, le=200)
    lexical_corpus_limit: int = Field(default=5000, ge=100, le=100000)


class RerankSettings(BaseSettings):
    """Document reranking settings."""

    model_config = SettingsConfigDict(extra="ignore")

    provider: Literal["noop", "hashing", "openai_compatible"] = "hashing"
    top_n: int = Field(default=8, ge=1, le=50)
    model: str = "contextforge-hash-reranker-v1"
    base_url: str = "https://api.openai.com/v1"
    api_key: SecretStr | None = None
    timeout_seconds: float = Field(default=30.0, gt=0)
    max_retries: int = Field(default=2, ge=0, le=10)
    retry_backoff_seconds: float = Field(default=0.5, gt=0)


class LlmSettings(BaseSettings):
    """LLM provider settings for answer generation."""

    model_config = SettingsConfigDict(extra="ignore")

    provider: Literal["mock", "openai", "azure_openai", "openai_compatible"] = "mock"
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    api_key: SecretStr | None = None
    azure_endpoint: str = ""
    azure_api_version: str = "2024-10-21"
    azure_deployment: str = ""
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=1024, ge=16, le=16000)
    timeout_seconds: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=2, ge=0, le=10)
    retry_backoff_seconds: float = Field(default=0.5, gt=0)


class PromptSettings(BaseSettings):
    """Versioned prompt template settings."""

    model_config = SettingsConfigDict(extra="ignore")

    active_version: str = "v1"
    default_language: Literal["en", "tr"] = "en"


class ChatSettings(BaseSettings):
    """Enterprise chat conversation, messaging, and streaming settings."""

    model_config = SettingsConfigDict(extra="ignore")

    max_message_length: int = Field(default=8000, ge=1, le=32000)
    max_participants: int = Field(default=25, ge=1, le=500)
    default_language: Literal["en", "tr"] = "en"
    history_max_messages: int = Field(default=20, ge=1, le=200)
    memory_strategy: Literal["recent", "token_budget", "summary"] = "token_budget"
    memory_token_budget: int = Field(default=2000, ge=128, le=32000)
    memory_summary_trigger_messages: int = Field(default=30, ge=2, le=1000)
    memory_summary_recent_messages: int = Field(default=6, ge=1, le=100)
    suggestion_count: int = Field(default=4, ge=1, le=10)
    stream_heartbeat_seconds: float = Field(default=15.0, gt=0)
    export_max_messages: int = Field(default=5000, ge=1, le=100000)


class AdminSettings(BaseSettings):
    """Administration, governance, retention, and cost-analytics settings.

    Env keys follow the single-underscore nested delimiter, e.g.
    ``CONTEXTFORGE_ADMIN_RETENTION_ENABLED`` and
    ``CONTEXTFORGE_ADMIN_CACHE_TTL_SECONDS``.
    """

    model_config = SettingsConfigDict(extra="ignore")

    retention_enabled: bool = True
    retention_batch_size: int = Field(default=500, ge=1, le=10000)
    retention_default_days: int = Field(default=365, ge=1, le=36500)
    retention_worker_interval_seconds: float = Field(default=3600.0, gt=0)
    cache_ttl_seconds: int = Field(default=30, ge=0, le=3600)
    token_usage_rollup_enabled: bool = True
    token_pricing_currency: str = Field(default="USD", min_length=3, max_length=3)
    llm_test_timeout_seconds: float = Field(default=5.0, gt=0, le=60.0)

    @field_validator("token_pricing_currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value


class SecuritySettings(BaseSettings):
    """JWT and related auth settings reserved for real authentication."""

    model_config = SettingsConfigDict(extra="ignore")

    secret_key: SecretStr = SecretStr("change-me-local-only-not-for-production")
    access_token_expire_minutes: int = Field(default=60, ge=1)
    algorithm: str = "HS256"


class RateLimitSettings(BaseSettings):
    """HTTP rate limiting for ``/api/v1`` routes.

    Env keys: ``CONTEXTFORGE_RATE_LIMIT_ENABLED``,
    ``CONTEXTFORGE_RATE_LIMIT_REQUESTS``, ``CONTEXTFORGE_RATE_LIMIT_WINDOW_SECONDS``,
    ``CONTEXTFORGE_RATE_LIMIT_BACKEND`` (``memory`` | ``redis``).
    """

    model_config = SettingsConfigDict(extra="ignore")

    enabled: bool = True
    requests: int = Field(default=120, ge=1, le=1_000_000)
    window_seconds: int = Field(default=60, ge=1, le=86_400)
    backend: Literal["memory", "redis"] = "memory"
    redis_key_prefix: str = "contextforge:ratelimit"
    exclude_path_prefixes: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["/api/v1/health"]
    )

    @field_validator("exclude_path_prefixes", mode="before")
    @classmethod
    def parse_exclude_prefixes(cls, value: object) -> list[str]:
        if value is None or value == "":
            return ["/api/v1/health"]
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                import json

                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            return [item.strip() for item in stripped.split(",") if item.strip()]
        msg = "exclude_path_prefixes must be a list or comma-separated string"
        raise TypeError(msg)


class ObservabilitySettings(BaseSettings):
    """Metrics and observability settings.

    Env keys: ``CONTEXTFORGE_OBSERVABILITY_METRICS_ENABLED``,
    ``CONTEXTFORGE_OBSERVABILITY_METRICS_PATH``.
    """

    model_config = SettingsConfigDict(extra="ignore")

    metrics_enabled: bool = True
    metrics_path: str = "/metrics"
    dependency_gauge_enabled: bool = True


class Settings(BaseSettings):
    """Root settings aggregating all nested configuration sections."""

    model_config = SettingsConfigDict(
        env_prefix="CONTEXTFORGE_",
        env_nested_delimiter="_",
        env_nested_max_split=1,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app: AppSettings = Field(default_factory=AppSettings)
    api: APISettings = Field(default_factory=APISettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    minio: MinioSettings = Field(default_factory=MinioSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    ingestion: IngestionSettings = Field(default_factory=IngestionSettings)
    rag: RagSettings = Field(default_factory=RagSettings)
    rerank: RerankSettings = Field(default_factory=RerankSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
    prompts: PromptSettings = Field(default_factory=PromptSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    chat: ChatSettings = Field(default_factory=ChatSettings)
    admin: AdminSettings = Field(default_factory=AdminSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    @model_validator(mode="after")
    def apply_environment_defaults(self) -> Settings:
        if self.app.environment == Environment.PRODUCTION:
            if self.api.docs_enabled:
                object.__setattr__(
                    self.api,
                    "docs_enabled",
                    False,
                )
            if self.logging.format == "console":
                object.__setattr__(
                    self.logging,
                    "format",
                    "json",
                )
        if self.app.environment == Environment.TEST:
            object.__setattr__(self.app, "debug", True)
            object.__setattr__(self.llm, "provider", "mock")
            object.__setattr__(self.rerank, "provider", "hashing")
            object.__setattr__(self.rate_limit, "enabled", False)
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache application settings."""
    return Settings()


def clear_settings_cache() -> None:
    """Clear the settings cache (useful for tests)."""
    get_settings.cache_clear()
