# Architecture overview

ContextForge is implemented as a modular monolith.

## Layer responsibilities

| Layer | Responsibility |
| --- | --- |
| `api` | HTTP routes, request/response schemas, middleware |
| `application` | Use cases, ports, application services |
| `domain` | Entities, domain errors, domain rules |
| `infrastructure` | Database, Redis, Qdrant, MinIO, queue adapters |
| `shared` | Settings, logging, shared utilities |
| `bootstrap` | Application factory and lifespan |
| `workers` | Long-running background processes (ingestion) |

## RAG flow

```mermaid
sequenceDiagram
  participant Client
  participant API
  participant Hybrid as HybridRetrieval
  participant Rerank
  participant LLM
  Client->>API: POST /rag/query
  API->>API: rag:query + KS authz
  API->>Hybrid: dense + BM25 fuse
  Hybrid-->>API: candidates
  API->>Rerank: reorder top-N
  Rerank-->>API: context chunks
  API->>LLM: system + untrusted context + question
  LLM-->>API: answer
  API-->>Client: answer + citations + diagnostics
```

## Dependency rule

* `domain` depends on nothing outside the domain/shared primitives
* `application` depends on domain and ports
* `infrastructure` implements application ports
* `api` depends on application services via FastAPI dependencies
* `workers` reuse application services and infrastructure adapters

## Timezone policy

All backend timestamps are stored and processed in UTC. User-facing timezone conversion
belongs at presentation boundaries.
