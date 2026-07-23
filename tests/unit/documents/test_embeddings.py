"""Unit tests for multilingual language detection and hashing embeddings."""

from __future__ import annotations

import pytest

from contextforge.infrastructure.embeddings.hashing_provider import (
    HashingMultilingualEmbeddingProvider,
)
from contextforge.infrastructure.embeddings.retry import retry_async
from contextforge.modules.documents.domain.exceptions import TransientEmbeddingError
from contextforge.modules.documents.domain.language import detect_language
from contextforge.shared.config.settings import EmbeddingSettings


@pytest.mark.unit
def test_detect_language_turkish_and_english() -> None:
    assert detect_language("Bu bir Turkce belgedir: \u011f\u00fc\u015f\u0131\u00f6\u00e7.") == "tr"
    assert detect_language("This is a plain English knowledge article.") == "en"
    assert detect_language("   ") == "und"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hashing_provider_is_deterministic_and_language_aware() -> None:
    provider = HashingMultilingualEmbeddingProvider(EmbeddingSettings(dimensions=32))
    first = await provider.embed_texts(["Merhaba dunya"], language="tr")
    second = await provider.embed_texts(["Merhaba dunya"], language="tr")
    english = await provider.embed_texts(["Merhaba dunya"], language="en")
    assert first.vectors[0] == second.vectors[0]
    assert first.vectors[0] != english.vectors[0]
    assert len(first.vectors[0]) == 32
    assert abs(sum(value * value for value in first.vectors[0]) - 1.0) < 1e-6


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_async_retries_transient_errors() -> None:
    attempts = {"count": 0}

    async def flaky() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise TransientEmbeddingError("temporary")
        return "ok"

    result = await retry_async(
        flaky,
        max_retries=3,
        backoff_seconds=0.01,
        retry_on=(TransientEmbeddingError,),
    )
    assert result == "ok"
    assert attempts["count"] == 3
