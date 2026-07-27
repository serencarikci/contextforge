# ADR-010: LLM Provider Abstraction

## Status

Accepted

## Context

RAG answering must not hard-depend on a single model vendor. Local development and CI need
deterministic offline behavior, while production may use OpenAI, Azure OpenAI, or local
OpenAI-compatible servers.

## Decision

Introduce `LlmProviderPort` with:

- `complete`, `stream`, `count_tokens`, and `model`
- Providers: `mock`, `openai`, `azure_openai`, `openai_compatible`
- Shared retries/timeouts via settings (`CONTEXTFORGE_LLM__*`)
- Factory `build_llm_provider(settings)` selected by configuration

Test and default local environments use `mock`.

## Consequences

- Application/RAG pipeline stays vendor-neutral
- Streaming is available through `/api/v1/rag/query/stream`
- Token counts are estimated when providers omit usage metadata
