"""Port for large language model completion and streaming."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class LlmMessage:
    """One chat message exchanged with an LLM provider."""

    role: str
    content: str


@dataclass(frozen=True, slots=True)
class LlmUsage:
    """Token accounting for an LLM call."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class LlmCompletion:
    """Non-streaming completion result."""

    content: str
    model: str
    usage: LlmUsage
    finish_reason: str | None = None


class LlmProviderError(Exception):
    """Base LLM provider failure."""

    def __init__(self, message: str, *, code: str = "LLM_PROVIDER_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class TransientLlmError(LlmProviderError):
    """Retryable LLM provider failure."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="LLM_PROVIDER_TRANSIENT")


class PermanentLlmError(LlmProviderError):
    """Non-retryable LLM provider failure."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="LLM_PROVIDER_ERROR")


class LlmProviderPort(Protocol):
    """Vendor-neutral LLM completion interface."""

    @property
    def model(self) -> str:
        """Configured model or deployment name."""
        ...

    def count_tokens(self, text: str) -> int:
        """Estimate token count for budgeting and observability."""
        ...

    async def complete(
        self,
        messages: list[LlmMessage],
        *,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> LlmCompletion:
        """Generate a full completion."""
        ...

    def stream(
        self,
        messages: list[LlmMessage],
        *,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream completion text deltas."""
        ...


__all__ = [
    "LlmCompletion",
    "LlmMessage",
    "LlmProviderError",
    "LlmProviderPort",
    "LlmUsage",
    "PermanentLlmError",
    "TransientLlmError",
]
