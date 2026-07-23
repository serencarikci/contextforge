"""Factory for configured embedding providers."""

from __future__ import annotations

from contextforge.application.ports.embedding_provider import EmbeddingProviderPort
from contextforge.infrastructure.embeddings.hashing_provider import (
    HashingMultilingualEmbeddingProvider,
)
from contextforge.infrastructure.embeddings.openai_compatible_provider import (
    OpenAICompatibleEmbeddingProvider,
)
from contextforge.shared.config.settings import EmbeddingSettings


def build_embedding_provider(settings: EmbeddingSettings) -> EmbeddingProviderPort:
    """Build the embedding provider selected by settings."""
    if settings.provider == "openai_compatible":
        return OpenAICompatibleEmbeddingProvider(settings)
    return HashingMultilingualEmbeddingProvider(settings)


__all__ = ["build_embedding_provider"]
