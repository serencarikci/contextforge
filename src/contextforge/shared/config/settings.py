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
    version: str = "0.1.0"

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


class SecuritySettings(BaseSettings):
    """Security placeholders for future authentication."""

    model_config = SettingsConfigDict(extra="ignore")

    secret_key: SecretStr = SecretStr("change-me-local-only-not-for-production")
    access_token_expire_minutes: int = Field(default=60, ge=1)
    algorithm: str = "HS256"


class Settings(BaseSettings):
    """Root settings aggregating all nested configuration sections."""

    model_config = SettingsConfigDict(
        env_prefix="CONTEXTFORGE_",
        env_nested_delimiter="__",
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
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

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
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache application settings."""
    return Settings()


def clear_settings_cache() -> None:
    """Clear the settings cache (useful for tests)."""
    get_settings.cache_clear()
