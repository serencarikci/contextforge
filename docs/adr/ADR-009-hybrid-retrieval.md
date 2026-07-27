# ADR-009: Hybrid Retrieval (Dense + BM25)

## Status

Accepted

## Context

ContextForge stores multilingual chunk embeddings in Qdrant and chunk text in PostgreSQL.
Phase 2 requires retrieval that works for both semantic paraphrases and exact keyword matches
under strict multi-tenant authorization.

## Decision

Implement hybrid retrieval:

1. Dense search via Qdrant filtered by `organization_id` and `knowledge_space_id`
2. Lexical Okapi BM25 over authorized chunk text loaded from PostgreSQL (`rank-bm25`)
3. Score fusion with configurable weights (`CONTEXTFORGE_RAG__DENSE_WEIGHT` /
   `LEXICAL_WEIGHT`) or Reciprocal Rank Fusion (`FUSION_METHOD=rrf`)
4. Pagination (`limit`/`offset`) after fusion
5. Mandatory post-filter with `RequestContext.can_access_knowledge_space`

Query embeddings reuse the existing `EmbeddingProviderPort`.

## Consequences

- Retrieval quality improves for mixed semantic/keyword queries
- Lexical corpus size is bounded by `LEXICAL_CORPUS_LIMIT`
- Application code depends on ports only; Qdrant/BM25 stay in infrastructure
