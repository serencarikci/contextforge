# ADR-011: RAG Security Boundaries

## Status

Accepted

## Context

Uploaded documents and end-user questions are untrusted. A RAG system that concatenates
document text into prompts is exposed to prompt injection and cross-tenant leakage risks.

## Decision

Enforce these controls in the RAG path:

1. Authorization gate: `rag:query` permission
2. Knowledge-space allow-list from `RequestContext` before and after retrieval
3. Sanitize user questions (strip control chars / common injection phrases)
4. Wrap every retrieved excerpt as `UNTRUSTED_DOCUMENT_BEGIN/END`
5. Keep system prompt immutable and separate from document content
6. Cap context size (`MAX_CONTEXT_TOKENS`, `MAX_CHUNKS_IN_CONTEXT`)
7. Return safe client errors without stack traces or foreign-tenant data

Prompt templates are versioned YAML files, not hardcoded strings in Python.

## Consequences

- Document text cannot override the system prompt by construction
- Restricted knowledge spaces remain invisible without membership/role grants
- Observability records timings/token counts without logging raw secrets
