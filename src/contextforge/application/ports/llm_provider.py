from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class LlmMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class LlmUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class LlmCompletion:
    content: str
    model: str
    usage: LlmUsage
    finish_reason: str | None = None


class LlmProviderError(Exception):
    def __init__(self, message: str, *, code: str = "LLM_PROVIDER_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class TransientLlmError(LlmProviderError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="LLM_PROVIDER_TRANSIENT")


class PermanentLlmError(LlmProviderError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="LLM_PROVIDER_ERROR")


class LlmProviderPort(Protocol):
    @property
    def model(self) -> str: ...

    def count_tokens(self, text: str) -> int: ...

    async def complete(
        self,
        messages: list[LlmMessage],
        *,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> LlmCompletion: ...

    def stream(
        self,
        messages: list[LlmMessage],
        *,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> AsyncIterator[str]: ...


__all__ = [
    "LlmCompletion",
    "LlmMessage",
    "LlmProviderError",
    "LlmProviderPort",
    "LlmUsage",
    "PermanentLlmError",
    "TransientLlmError",
]
