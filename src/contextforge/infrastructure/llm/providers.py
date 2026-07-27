"""LLM provider implementations (mock, OpenAI, Azure, OpenAI-compatible)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from contextforge.application.ports.llm_provider import (
    LlmCompletion,
    LlmMessage,
    LlmUsage,
    PermanentLlmError,
    TransientLlmError,
)
from contextforge.shared.config.settings import LlmSettings
from contextforge.shared.utilities.retry import retry_async
from contextforge.shared.utilities.tokens import estimate_tokens


class MockLlmProvider:
    """Deterministic offline LLM used for local/test environments."""

    def __init__(self, settings: LlmSettings) -> None:
        self._settings = settings

    @property
    def model(self) -> str:
        return self._settings.model or "mock-llm"

    def count_tokens(self, text: str) -> int:
        return estimate_tokens(text)

    @staticmethod
    def _extract_question(user_content: str) -> str:
        """Pull the user question without echoing untrusted document wrappers."""
        text = user_content or ""
        lower = text.lower()
        start = lower.find("question:")
        if start >= 0:
            text = text[start + len("question:") :]
        end_markers = (
            "authorized excerpts",
            "untrusted_document_begin",
            "untrusted_document_end",
        )
        cut = len(text)
        lower_tail = text.lower()
        for marker in end_markers:
            idx = lower_tail.find(marker)
            if idx >= 0:
                cut = min(cut, idx)
        cleaned = text[:cut].strip()
        return cleaned[:240]

    async def complete(
        self,
        messages: list[LlmMessage],
        *,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> LlmCompletion:
        del temperature, max_output_tokens
        user_content = next((m.content for m in reversed(messages) if m.role == "user"), "")
        question = self._extract_question(user_content)
        citations: list[str] = []
        for message in messages:
            for line in message.content.splitlines():
                stripped = line.strip()
                if stripped.startswith("[cite:") and "untrusted" not in stripped.lower():
                    citations.append(stripped)
        citation_text = " ".join(citations[:3]) if citations else ""
        answer = (
            "Based on the authorized knowledge base, here is a grounded answer. "
            f"Question summary: {question}"
        )
        if citation_text:
            answer = f"{answer}\n\nSources: {citation_text}"
        prompt_tokens = sum(self.count_tokens(m.content) for m in messages)
        completion_tokens = self.count_tokens(answer)
        usage = LlmUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        return LlmCompletion(content=answer, model=self.model, usage=usage, finish_reason="stop")

    async def stream(
        self,
        messages: list[LlmMessage],
        *,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        completion = await self.complete(
            messages, temperature=temperature, max_output_tokens=max_output_tokens
        )
        text = completion.content
        size = 40
        for index in range(0, len(text), size):
            yield text[index : index + size]


class OpenAICompatibleLlmProvider:
    """Chat Completions client for OpenAI-compatible HTTP APIs (incl. local)."""

    def __init__(self, settings: LlmSettings, *, base_url: str | None = None) -> None:
        self._settings = settings
        self._base_url = (base_url or settings.base_url).rstrip("/")
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if settings.api_key is not None:
            secret = settings.api_key.get_secret_value()
            if secret:
                headers["Authorization"] = f"Bearer {secret}"
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=settings.timeout_seconds,
        )

    @property
    def model(self) -> str:
        return self._settings.model

    def count_tokens(self, text: str) -> int:
        return estimate_tokens(text)

    async def complete(
        self,
        messages: list[LlmMessage],
        *,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> LlmCompletion:
        async def _call() -> LlmCompletion:
            payload = {
                "model": self.model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "temperature": self._settings.temperature if temperature is None else temperature,
                "max_tokens": self._settings.max_output_tokens
                if max_output_tokens is None
                else max_output_tokens,
            }
            response = await self._client.post("/chat/completions", json=payload)
            if response.status_code >= 500:
                raise TransientLlmError(f"LLM unavailable: HTTP {response.status_code}")
            if response.status_code >= 400:
                raise PermanentLlmError(f"LLM rejected request: HTTP {response.status_code}")
            body = response.json()
            choices = body.get("choices") or []
            if not choices:
                raise PermanentLlmError("LLM returned no choices.")
            message = choices[0].get("message") or {}
            content = str(message.get("content") or "")
            usage_body = body.get("usage") or {}
            usage = LlmUsage(
                prompt_tokens=int(usage_body.get("prompt_tokens") or self.count_tokens("")),
                completion_tokens=int(
                    usage_body.get("completion_tokens") or self.count_tokens(content)
                ),
                total_tokens=int(
                    usage_body.get("total_tokens")
                    or (
                        int(usage_body.get("prompt_tokens") or 0)
                        + int(usage_body.get("completion_tokens") or 0)
                    )
                ),
            )
            if usage.total_tokens == 0:
                usage = LlmUsage(
                    prompt_tokens=sum(self.count_tokens(m.content) for m in messages),
                    completion_tokens=self.count_tokens(content),
                    total_tokens=sum(self.count_tokens(m.content) for m in messages)
                    + self.count_tokens(content),
                )
            return LlmCompletion(
                content=content,
                model=str(body.get("model") or self.model),
                usage=usage,
                finish_reason=choices[0].get("finish_reason"),
            )

        return await retry_async(
            _call,
            max_retries=self._settings.max_retries,
            backoff_seconds=self._settings.retry_backoff_seconds,
            retry_on=(TransientLlmError, httpx.TransportError, httpx.TimeoutException),
        )

    async def stream(
        self,
        messages: list[LlmMessage],
        *,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": self._settings.temperature if temperature is None else temperature,
            "max_tokens": self._settings.max_output_tokens
            if max_output_tokens is None
            else max_output_tokens,
            "stream": True,
        }
        try:
            async with self._client.stream("POST", "/chat/completions", json=payload) as response:
                if response.status_code >= 400:
                    detail = await response.aread()
                    raise PermanentLlmError(
                        f"LLM stream rejected: HTTP {response.status_code} {detail!r}"
                    )
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if data == "[DONE]":
                        break
                    import json

                    chunk = json.loads(data)
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    if content:
                        yield str(content)
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            raise TransientLlmError(str(exc)) from exc

    async def close(self) -> None:
        await self._client.aclose()


class OpenAILlmProvider(OpenAICompatibleLlmProvider):
    """OpenAI public API provider."""

    def __init__(self, settings: LlmSettings) -> None:
        super().__init__(settings, base_url=settings.base_url or "https://api.openai.com/v1")


class AzureOpenAILlmProvider:
    """Azure OpenAI chat completions provider."""

    def __init__(self, settings: LlmSettings) -> None:
        self._settings = settings
        endpoint = settings.azure_endpoint.rstrip("/")
        if not endpoint:
            raise PermanentLlmError("Azure OpenAI endpoint is required.")
        deployment = settings.azure_deployment or settings.model
        self._deployment = deployment
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if settings.api_key is not None:
            secret = settings.api_key.get_secret_value()
            if secret:
                headers["api-key"] = secret
        self._client = httpx.AsyncClient(
            base_url=endpoint,
            headers=headers,
            timeout=settings.timeout_seconds,
        )
        self._api_version = settings.azure_api_version

    @property
    def model(self) -> str:
        return self._deployment

    def count_tokens(self, text: str) -> int:
        return estimate_tokens(text)

    async def complete(
        self,
        messages: list[LlmMessage],
        *,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> LlmCompletion:
        path = f"/openai/deployments/{self._deployment}/chat/completions"

        async def _call() -> LlmCompletion:
            payload = {
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "temperature": self._settings.temperature if temperature is None else temperature,
                "max_tokens": self._settings.max_output_tokens
                if max_output_tokens is None
                else max_output_tokens,
            }
            response = await self._client.post(
                path, params={"api-version": self._api_version}, json=payload
            )
            if response.status_code >= 500:
                raise TransientLlmError(f"Azure LLM unavailable: HTTP {response.status_code}")
            if response.status_code >= 400:
                raise PermanentLlmError(f"Azure LLM rejected request: HTTP {response.status_code}")
            body = response.json()
            choices = body.get("choices") or []
            if not choices:
                raise PermanentLlmError("Azure LLM returned no choices.")
            content = str((choices[0].get("message") or {}).get("content") or "")
            usage_body = body.get("usage") or {}
            usage = LlmUsage(
                prompt_tokens=int(
                    usage_body.get("prompt_tokens")
                    or sum(self.count_tokens(m.content) for m in messages)
                ),
                completion_tokens=int(
                    usage_body.get("completion_tokens") or self.count_tokens(content)
                ),
                total_tokens=int(
                    usage_body.get("total_tokens")
                    or (
                        int(usage_body.get("prompt_tokens") or 0)
                        + int(usage_body.get("completion_tokens") or 0)
                    )
                ),
            )
            return LlmCompletion(
                content=content,
                model=self.model,
                usage=usage,
                finish_reason=choices[0].get("finish_reason"),
            )

        return await retry_async(
            _call,
            max_retries=self._settings.max_retries,
            backoff_seconds=self._settings.retry_backoff_seconds,
            retry_on=(TransientLlmError, httpx.TransportError, httpx.TimeoutException),
        )

    async def stream(
        self,
        messages: list[LlmMessage],
        *,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        path = f"/openai/deployments/{self._deployment}/chat/completions"
        payload = {
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": self._settings.temperature if temperature is None else temperature,
            "max_tokens": self._settings.max_output_tokens
            if max_output_tokens is None
            else max_output_tokens,
            "stream": True,
        }
        try:
            async with self._client.stream(
                "POST", path, params={"api-version": self._api_version}, json=payload
            ) as response:
                if response.status_code >= 400:
                    detail = await response.aread()
                    raise PermanentLlmError(
                        f"Azure LLM stream rejected: HTTP {response.status_code} {detail!r}"
                    )
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if data == "[DONE]":
                        break
                    import json

                    chunk = json.loads(data)
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    if content:
                        yield str(content)
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            raise TransientLlmError(str(exc)) from exc

    async def close(self) -> None:
        await self._client.aclose()


def build_llm_provider(
    settings: LlmSettings,
) -> MockLlmProvider | OpenAILlmProvider | AzureOpenAILlmProvider | OpenAICompatibleLlmProvider:
    if settings.provider == "openai":
        return OpenAILlmProvider(settings)
    if settings.provider == "azure_openai":
        return AzureOpenAILlmProvider(settings)
    if settings.provider == "openai_compatible":
        return OpenAICompatibleLlmProvider(settings)
    return MockLlmProvider(settings)


__all__ = [
    "AzureOpenAILlmProvider",
    "MockLlmProvider",
    "OpenAICompatibleLlmProvider",
    "OpenAILlmProvider",
    "build_llm_provider",
]
