# ContextForge — Multilingual Enterprise Knowledge Assistant

Secure enterprise knowledge platform where organizations upload project documents,
technical documentation, support records, API specifications, architecture documents,
and operational guides. Users later ask questions in Turkish or English and receive
answers grounded in authorized company documents.

> **Current scope:** identity, multi-tenancy, RBAC, audit logging, document upload/storage,
> parsing, semantic chunking, multilingual embeddings (Qdrant), background ingestion
> workers, hybrid RAG answering, multi-turn enterprise chat (streaming, memory,
> feedback, and analytics), Phase 4 administration/governance, Phase 5 production
> engineering (Docker/Helm/Terraform, metrics, rate limits, CI/CD, backups, runbooks),
> and Phase 6 Next.js enterprise web UI (`frontend/web`) are implemented.
>
> **Authentication:** identity is resolved via development-only HTTP headers (see
> [Development identity headers](#development-identity-headers)), gated off in
> `staging`/`production`. It is **not** a substitute for real authentication (OIDC/SSO) —
> see [Auth roadmap](#auth-roadmap).

## Long-term product vision

* Upload and govern enterprise documents
* Enforce authorization boundaries over knowledge
* Retrieve grounded context from approved sources
* Answer questions in Turkish and English
* Provide auditability and operational visibility

## Current scope

* FastAPI application factory and lifespan
* Modular Clean Architecture layout
* Async PostgreSQL + SQLAlchemy 2 + Alembic
* Redis, Qdrant, and MinIO infrastructure wiring
* Health, readiness, and system info endpoints
* Structured logging and correlation IDs
* Docker / Docker Compose
* **Organization multi-tenancy** — organizations, memberships, and every business
 entity scoped by `organization_id`
* **Scoped RBAC** — system + custom roles, permissions, org/project/knowledge-space-scoped
 role assignments
* **Development identity** — header-based caller identity for local/test/development
 only
* **Customers, projects, and knowledge spaces** — core tenant business entities, with
 knowledge-space visibility rules (`organization` vs `restricted`)
* **Append-only audit trail** — every mutation is durably recorded with sanitized
 metadata
* **Document pipeline** — MinIO upload/storage, PDF/DOCX/HTML/Markdown parsing, semantic
 chunking, multilingual embeddings into Qdrant
* **Background ingestion workers** — Redis-backed jobs that run parse → chunk → embed with
 retries and failed-job recovery (`make worker` / Compose `ingestion-worker`)
* **Hybrid RAG** — dense (Qdrant) + BM25 lexical retrieval, reranking, provider-neutral LLM
 answering with citations, prompt versioning, and injection-resistant context assembly
* **Enterprise chat** — multi-turn conversations grounded via `RagQueryService`, pluggable
 memory strategies, SSE streaming with cooperative cancellation, message idempotency,
 per-message knowledge-space revalidation, feedback, export (JSON/Markdown), and
 usage analytics
* **Administration & governance (Phase 4)** — `/api/v1/admin/*` dashboard, user list,
 org quotas/settings, custom role permissions, document/ingestion ops, audit export,
 usage/token cost analytics, prompt versioning, LLM provider configs (masked secrets),
 feature flags (Redis cache), ops overview, and retention policies/worker
 (`contextforge-retention-worker`)
* **Production engineering (Phase 5)** — hardened Docker/Compose (incl. retention +
 `obs` profile), security headers, rate limiting, Prometheus `/metrics`, Helm chart,
 provider-neutral Terraform stubs, CD to GHCR, backups/DR scripts, k6 scenarios, and
 ops runbooks under `ops/runbooks/`
* **Enterprise web UI (Phase 6)** — Next.js 15 / React 19 app in `frontend/web` with
 App Router, TanStack Query + Zustand, i18n (EN/TR), light/dark theme, chat SSE,
 documents, knowledge spaces, admin, analytics, and system ops pages
* Pytest (unit, integration, architecture, authorization, security, API)
* Ruff, mypy, pre-commit, GitHub Actions CI/CD

## Frontend (Phase 6)

The production web client lives in [`frontend/web`](frontend/web).

```mermaid
flowchart LR
  Browser[Browser] --> Web[Next.js web :3001]
  Web -->|X-ContextForge-* headers| API[FastAPI :8000]
  API --> PG[(PostgreSQL)]
  API --> Qdrant[(Qdrant)]
  API --> MinIO[(MinIO)]
```

### Stack

* Next.js 15 (App Router), React 19, TypeScript strict
* Tailwind CSS + shadcn-style Radix primitives
* TanStack Query (server state), Zustand (session/UI)
* React Hook Form + Zod, Axios, i18next (EN/TR), next-themes
* Vitest unit tests, Playwright e2e scaffold

### Local development

```bash
# API + infra
make up
make bootstrap-dev

# Frontend
cd frontend/web
cp .env.example .env.local
npm install
npm run dev          # http://localhost:3001
```

Sign in with bootstrap presets (`admin@contextforge.local` / `developer@contextforge.local`)
or any valid user UUID after bootstrap. The UI stores a client session and sends the
backend development identity headers on every API call.

Compose also builds the `web` service on port **3001** (`NEXT_PUBLIC_API_BASE_URL`
should point at the browser-reachable API URL, typically `http://localhost:8000`).

### Frontend commands

```bash
cd frontend/web
npm run lint
npm run type-check
npm test
npm run build
docker build -t contextforge-web .
```

### UI map

| Area | Routes |
| --- | --- |
| Auth | `/login`, `/logout`, `/forgot-password`, `/reset-password`, `/session-expired`, `/unauthorized` |
| Chat | `/chat`, `/chat/[conversationId]` (SSE streaming) |
| Documents | `/documents`, `/documents/upload` |
| Knowledge spaces | `/knowledge-spaces`, `/new`, `/[id]` |
| Tenancy | `/customers`, `/projects` |
| Admin | `/admin/*` users, roles, prompts, LLM, flags, audit, retention… |
| Analytics / System | `/analytics`, `/system`, `/settings` |

CORS must allow `http://localhost:3001` and the `X-ContextForge-*` headers (wired in
API middleware + `.env.example`).

### UI screens & operations

Screenshots live under [`docs/screenshots/ui/`](docs/screenshots/ui/). Regenerate them with the
API + web running (`:8001` / `:3001` in local hybrid mode, or compose ports):

```bash
cd frontend/web
npm install
npx playwright install chromium   # once
node scripts/capture-ui-screenshots.mjs
```

#### 1. Sign in (`/login`)

![Sign in](docs/screenshots/ui/01-login.png)

1. Open `http://localhost:3001/login`.
2. Click **Use bootstrap account / Dev Admin** or **Dev Developer** for instant local sign-in
   (no password; client session + `X-ContextForge-*` headers).
3. Or type an email/user UUID, wait for organizations to load, pick an org, then **Sign in**.
4. Use **Forgot session?** to reach the recovery flow.

#### 2. Forgot session (`/forgot-password`)

![Forgot password](docs/screenshots/ui/02-forgot-password.png)

1. Enter email or user ID.
2. Submit to continue to reset (dev UI only — no real email).

#### 3. Reset session (`/reset-password`)

![Reset password](docs/screenshots/ui/03-reset-password.png)

1. Confirm identity from the query string / form.
2. Complete the form to return to login with a fresh client session path.

#### 4. Session expired (`/session-expired`)

![Session expired](docs/screenshots/ui/04-session-expired.png)

Shown when the client session TTL expires. Click through to `/login` and sign in again.

#### 5. Unauthorized (`/unauthorized`)

![Unauthorized](docs/screenshots/ui/05-unauthorized.png)

Shown when the signed-in user lacks the permission for a route. Switch account/org or ask an admin
for the required RBAC permission.

#### 6. Chat list (`/chat`)

![Chat list](docs/screenshots/ui/06-chat.png)

1. Sidebar → **Chat**.
2. Click **New conversation** to create a thread (optionally scoped to the session knowledge space).
3. Search by title; filter **Active** / **Archived**.
4. Open a row to enter the conversation workspace.
5. Row menu: pin / archive / restore / delete (permission-gated).

#### 7. Conversation (`/chat/[conversationId]`)

![Conversation](docs/screenshots/ui/07-chat-conversation.png)

1. Type a question in the composer and **Send** (SSE streaming reply).
2. Open **Sources** to inspect RAG citations for the latest answer.
3. Use **Export** to download the transcript.
4. Switch threads from the left list without leaving chat.

#### 8. Documents (`/documents`)

![Documents](docs/screenshots/ui/08-documents.png)

1. Sidebar → **Documents**.
2. Filter by search, status, and knowledge space.
3. Track lifecycle badges: document status, **Parse**, **Embedding**.
4. Row actions / bulk select for delete (and admin bulk ops when permitted).
5. Click **Upload documents** to start an upload.

#### 9. Upload documents (`/documents/upload`)

![Upload documents](docs/screenshots/ui/09-documents-upload.png)

1. Select a **Knowledge space**.
2. Drag-and-drop or pick files in the dropzone.
3. After upload, return to the documents list and wait for parse/embed jobs.

#### 10. Knowledge spaces (`/knowledge-spaces`)

![Knowledge spaces](docs/screenshots/ui/10-knowledge-spaces.png)

1. Sidebar → **Knowledge Spaces**.
2. Search / filter by status.
3. Open a row for detail, or **Create** for a new space.

#### 11. Create knowledge space (`/knowledge-spaces/new`)

![Create knowledge space](docs/screenshots/ui/11-knowledge-spaces-new.png)

1. Fill **Name**, **Slug**, optional **Description**.
2. Set **Visibility** and optional **Project**.
3. **Create** → detail page; **Cancel** returns to the list.

#### 12. Knowledge space detail (`/knowledge-spaces/[id]`)

![Knowledge space detail](docs/screenshots/ui/12-knowledge-space-detail.png)

1. **Overview**: review slug/visibility; edit name, description, visibility → **Save**.
2. **Members**: invite/remove members and roles for the space.
3. **Documents**: jump into documents scoped to this space.
4. **Statistics**: usage counters for the space.
5. **Archive** / **Back** from the header actions.

#### 13. Customers (`/customers`)

![Customers](docs/screenshots/ui/13-customers.png)

1. Open `/customers` (permission `customer:read`).
2. Review customer code, name, and status in the table.

#### 14. Projects (`/projects`)

![Projects](docs/screenshots/ui/14-projects.png)

1. Open `/projects` (permission `project:read`).
2. Review project rows for the current organization.

#### 15. Analytics (`/analytics`)

![Analytics](docs/screenshots/ui/15-analytics.png)

1. Sidebar → **Analytics**.
2. Change the time window (e.g. 7 / 30 days).
3. Inspect usage, token, and chat charts.
4. **Export** downloads analytics data when available.

#### 16. System (`/system`)

![System](docs/screenshots/ui/16-system.png)

1. Sidebar → **System**.
2. Check live/ready health and ops counters.
3. Filter ingestion jobs by status; refresh to poll worker progress.
4. Retry/cancel failed jobs when actions are offered.

#### 17. Settings (`/settings`)

![Settings](docs/screenshots/ui/17-settings.png)

1. Sidebar → **Settings**.
2. Update display name and preferred language → save.
3. Switch theme (light / dark / system) and organization context.
4. Header controls also toggle language and theme globally.

#### 18. Admin dashboard (`/admin`)

![Admin dashboard](docs/screenshots/ui/18-admin-dashboard.png)

1. Sidebar → **Administration** (needs `admin:dashboard`).
2. Read membership, document, conversation, and token stats.
3. Use the admin sub-nav for users, orgs, roles, prompts, LLM, flags, settings, audit, retention.
4. Drill into ingestion / ops cards when investigating pipeline health.

#### 19. Admin users (`/admin/users`)

![Admin users](docs/screenshots/ui/19-admin-users.png)

1. Search / filter users by status.
2. **Activate** or **Deactivate** accounts from row actions.

#### 20. Admin organizations (`/admin/organizations`)

![Admin organizations](docs/screenshots/ui/20-admin-organizations.png)

1. List organizations for the platform.
2. Open or update org metadata according to available admin actions.

#### 21. Admin roles (`/admin/roles`)

![Admin roles](docs/screenshots/ui/21-admin-roles.png)

1. Review role definitions and permission sets.
2. Create/update roles when `role:manage` / admin role permissions allow it.

#### 22. Admin prompts (`/admin/prompts`)

![Admin prompts](docs/screenshots/ui/22-admin-prompts.png)

1. Browse prompt templates used by RAG/chat.
2. Edit or version prompts where the admin UI exposes mutations.

#### 23. Admin LLM providers (`/admin/llm-providers`)

![Admin LLM providers](docs/screenshots/ui/23-admin-llm.png)

1. Inspect configured LLM providers and models.
2. Enable/disable or adjust provider settings for the org.

#### 24. Admin feature flags (`/admin/feature-flags`)

![Admin feature flags](docs/screenshots/ui/24-admin-feature-flags.png)

1. Toggle feature flags for staged rollouts.
2. Save changes and verify UI/API behavior for the flag.

#### 25. Admin audit (`/admin/audit`)

![Admin audit](docs/screenshots/ui/25-admin-audit.png)

1. Filter audit events by actor/action/time.
2. Inspect rows for compliance / incident review (`audit:read`).

#### 26. Admin retention (`/admin/retention`)

![Admin retention](docs/screenshots/ui/26-admin-retention.png)

1. Review retention policies for conversations/documents.
2. Update retention windows when `admin:retention` is granted.

#### 27. Admin settings (`/admin/settings`)

![Admin settings](docs/screenshots/ui/27-admin-settings.png)

1. Adjust organization-level admin settings.
2. Save and confirm via toast / refreshed values.

**Typical happy path:** sign in as Dev Admin → create/select a knowledge space → upload a document →
wait until parse/embed are healthy on System/Documents → open Chat → **New conversation** → ask a
question → open **Sources** for citations.

## Architecture overview

```mermaid
flowchart LR
 User[User / Client] --> API[ContextForge API]
 API --> PG[(PostgreSQL)]
 API --> Redis[(Redis)]
 API --> Qdrant[(Qdrant)]
 API --> MinIO[(MinIO)]
 Worker[Ingestion Worker] --> PG
 Worker --> Redis
 Worker --> Qdrant
 Worker --> MinIO
```

Conceptual layers:

* **API** — HTTP transport, middleware, schemas
* **Application** — use cases and ports
* **Domain** — entities and domain errors
* **Infrastructure** — PostgreSQL, Redis, Qdrant, MinIO adapters

## RAG and chat flows

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

```mermaid
sequenceDiagram
  participant Client
  participant API as Chat router
  participant ChatSvc as ChatService
  participant Memory as MemoryService
  participant Rag as RagQueryService
  Client->>API: POST /conversations/{id}/messages
  API->>ChatSvc: send_message
  ChatSvc->>Memory: build_history_context
  ChatSvc->>Rag: query(..., history_context)
  Rag-->>ChatSvc: answer + citations
  ChatSvc-->>API: ChatAnswer
  API-->>Client: user + assistant messages
```

## Identity & multi-tenancy overview

Every business entity in ContextForge is scoped to an **organization** (the tenant
boundary). A **user** can be a member of multiple organizations; each
`OrganizationMembership` is where roles are actually assigned, and where authorization
for a given request is resolved from.

```mermaid
erDiagram
 USER ||--o{ ORGANIZATION_MEMBERSHIP : "has"
 ORGANIZATION ||--o{ ORGANIZATION_MEMBERSHIP : "has"
 ORGANIZATION ||--o{ CUSTOMER : "owns"
 ORGANIZATION ||--o{ PROJECT : "owns"
 ORGANIZATION ||--o{ KNOWLEDGE_SPACE : "owns"
 ORGANIZATION ||--o{ ROLE : "defines (custom roles)"
 CUSTOMER ||--o{ PROJECT : "has"
 PROJECT ||--o{ KNOWLEDGE_SPACE : "may contain"
 ORGANIZATION_MEMBERSHIP ||--o{ ROLE_ASSIGNMENT : "granted"
 ROLE ||--o{ ROLE_ASSIGNMENT : "used in"
 ROLE ||--o{ ROLE_PERMISSION : "bundles"
 PERMISSION ||--o{ ROLE_PERMISSION : "granted by"
 ORGANIZATION_MEMBERSHIP ||--o{ KNOWLEDGE_SPACE_MEMBERSHIP : "granted"
 KNOWLEDGE_SPACE ||--o{ KNOWLEDGE_SPACE_MEMBERSHIP : "has"
 ORGANIZATION ||--o{ AUDIT_EVENT : "scopes"

 USER {
 uuid id
 string email
 string status
 bool is_platform_admin
 }
 ORGANIZATION {
 uuid id
 string slug
 string status
 }
 ORGANIZATION_MEMBERSHIP {
 uuid id
 uuid organization_id
 uuid user_id
 string status
 }
 ROLE {
 uuid id
 string code
 uuid organization_id "null for system roles"
 bool is_system
 }
 ROLE_ASSIGNMENT {
 uuid id
 uuid membership_id
 uuid role_id
 uuid project_id "nullable scope"
 uuid knowledge_space_id "nullable scope"
 }
 CUSTOMER {
 uuid id
 uuid organization_id
 string code
 }
 PROJECT {
 uuid id
 uuid organization_id
 uuid customer_id
 string key
 }
 KNOWLEDGE_SPACE {
 uuid id
 uuid organization_id
 uuid project_id "nullable"
 string visibility
 }
 KNOWLEDGE_SPACE_MEMBERSHIP {
 uuid id
 uuid knowledge_space_id
 uuid membership_id
 string access_level
 }
 AUDIT_EVENT {
 uuid id
 uuid organization_id
 uuid actor_user_id
 string action
 string resource_type
 }
```

Request-scoped authorization flow:

```mermaid
sequenceDiagram
 participant Client
 participant API as FastAPI dependency
 participant IdentitySvc as identity_context_service
 participant DB as PostgreSQL

 Client->>API: Request + X-ContextForge-User-ID / -Organization-ID
 API->>IdentitySvc: build_request_context(user_id, organization_id)
 IdentitySvc->>IdentitySvc: development_identity_enabled(settings)?
 alt disabled (staging/production)
 IdentitySvc-->>Client: 401 AUTHENTICATION_REQUIRED
 else enabled (local/test/development)
 IdentitySvc->>DB: load user, organization, membership
 IdentitySvc->>IdentitySvc: validate active status (user/org/membership)
 IdentitySvc->>DB: load org/project/KS-scoped permissions + accessible ids
 IdentitySvc-->>API: RequestContext (permissions, accessible ids)
 API->>API: service.method(uow, ctx, ...)
 API->>API: ctx.require_permission(...) / ctx.require_*_access(...)
 API-->>Client: 200 (or 403/404 per authorization result)
 end
```

## Technology stack

| Area | Choice |
| --- | --- |
| Language | Python 3.13 |
| API | FastAPI + Uvicorn |
| Settings | pydantic-settings |
| DB | PostgreSQL + SQLAlchemy 2 + asyncpg + Alembic |
| Cache / coordination | Redis |
| Vector store (future) | Qdrant |
| Object storage (future docs) | MinIO |
| Packaging | uv |
| Quality | Ruff, mypy, pytest, pre-commit |

## Repository structure

```text
src/contextforge/ Application source
migrations/ Alembic migrations
tests/ Unit, integration, architecture tests
infrastructure/ Docker/service helper assets
docs/ Architecture docs and ADRs
scripts/ Entrypoint and utility scripts
```

## Prerequisites

* Python 3.13
* [uv](https://docs.astral.sh/uv/)
* Docker and Docker Compose
* GNU Make (optional but recommended)

## Local installation

```bash
cp .env.example .env
make install
```

## Docker Compose startup

```bash
docker compose up --build
```

This starts:

* `api` on http://localhost:8000
* `ingestion-worker` (background document processing)
* `postgres` on localhost:5432
* `redis` on localhost:6379
* `qdrant` on localhost:6333
* `minio` on localhost:9000 (console on 9001)
* one-shot `migrate` and `minio-init` jobs

API docs (local/development): http://localhost:8000/docs

Stop:

```bash
make down
# or
docker compose down
```

## Environment variables

See `.env.example`. Nested settings use:

```text
CONTEXTFORGE_APP_ENVIRONMENT
CONTEXTFORGE_POSTGRES_HOST
CONTEXTFORGE_REDIS_URL
CONTEXTFORGE_QDRANT_URL
CONTEXTFORGE_MINIO_ENDPOINT
CONTEXTFORGE_CHAT_MEMORY_STRATEGY
CONTEXTFORGE_CHAT_MAX_MESSAGE_LENGTH
CONTEXTFORGE_CHAT_STREAM_HEARTBEAT_SECONDS
```

Supported environments: `local`, `test`, `development`, `staging`, `production`.

Docker Compose uses clearly marked **non-production** development credentials.

## Development identity headers

> ⚠️ **This is not production authentication.** It is a deliberate, environment-gated
> stand-in used only in `local`, `test`, and `development`.
> It is unconditionally disabled in
> `staging` and `production` — every request without real authentication is rejected
> with `401 AUTHENTICATION_REQUIRED` in those environments, regardless of headers sent.

Every authenticated endpoint resolves "who is calling, and on behalf of which
organization" from two request headers:

```text
X-ContextForge-User-ID: <uuid of an existing, active user>
X-ContextForge-Organization-ID: <uuid of an organization the user is an active member of>
```

Both are validated against the database on every request (user active, organization not
archived, membership active) — a syntactically valid but nonexistent/inactive id is
rejected the same as a missing header. There is no `X-ContextForge-Role` or
`X-ContextForge-Permissions` header — permissions are always computed server-side from
`RoleAssignment` rows; any role/permission header a client sends is simply ignored (see
`tests/security/test_role_headers_ignored.py`).

## `bootstrap-dev`

`make bootstrap-dev` seeds a deterministic local development tenant — safe to run
repeatedly (idempotent: looks up each entity by its natural key before creating it, and
produces the exact same UUIDs every time via `uuid5`):

```bash
make migrate # apply migrations first
make bootstrap-dev
```

It creates:

* organization `contextforge-dev`
* an `organization_admin` user (`admin@contextforge.local`) and a `developer` user
 (`developer@contextforge.local`), both active members
* a customer (`DEV-CUST`) and a project (`DEMO`) linked to it
* an organization-visible knowledge space (`company-handbook`) and a `restricted` one
 (`incident-playbooks`), with the developer granted `contributor` access to the
 restricted space

It prints the header values for the seeded admin user at the end:

```text
X-ContextForge-User-ID: <admin uuid>
X-ContextForge-Organization-ID: <org uuid>
```

Paste those into the `curl` examples below, or into the `Authorize`-adjacent headers of
`/docs`, to call the API as that user. `make seed-system-data` is a separate, read-only
sanity check that the RBAC permission/system-role reference catalog (seeded by migrations,
not by this script) is actually present, and prints their counts.

## Database migrations

```bash
make migrate # alembic upgrade head
make migration name="desc" # autogenerate revision
make downgrade # alembic downgrade -1
make worker # run ingestion worker locally
uv run alembic history
```

Compose applies migrations through the dedicated `migrate` service before the API starts.

## Test commands

```bash
make test
make test-unit
make test-integration
make test-architecture
make test-authorization
make test-security
make coverage
```

Integration tests expect local infrastructure (Compose) to be reachable on the default ports.
`test-authorization` and `test-security` run the `authorization`- and `security`-marked
suites under `tests/unit/authorization/` and `tests/security/` respectively (plus any other
test marked accordingly); `tests/api/` is marked `api` and exercised as part of `make test`.

## Lint and type-check

```bash
make lint
make format
make type-check
```

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/health/live` | Liveness (no infra dependency) |
| GET | `/api/v1/health/ready` | Readiness for PostgreSQL, Redis, Qdrant, MinIO |
| GET | `/api/v1/system/info` | Safe system metadata and capability flags |
| POST/GET | `/api/v1/organizations`, `/{id}`, `/{id}/suspend`, `/{id}/archive` | Organization lifecycle |
| POST | `/api/v1/users`, `/{id}`, `/{id}/suspend`, `/{id}/archive` | User provisioning/lifecycle |
| POST/GET/DELETE | `/api/v1/memberships`, `/{id}`, `/{id}/suspend` | Organization membership lifecycle |
| GET/POST/PATCH/DELETE | `/api/v1/roles`, `/{id}`, `/assignments`, `/assignments/{id}` | Roles and role assignments |
| POST/GET/PATCH | `/api/v1/customers`, `/{id}`, `/{id}/archive` | Customer lifecycle |
| POST/GET/PATCH | `/api/v1/projects`, `/{id}`, `/{id}/archive` | Project lifecycle |
| POST/GET/PATCH | `/api/v1/knowledge-spaces`, `/{id}`, `/{id}/archive` | Knowledge space lifecycle |
| POST/GET/PATCH/DELETE | `/api/v1/knowledge-spaces/{id}/memberships`, `/{ks_membership_id}` | Knowledge-space membership |
| POST/GET/PATCH/PUT/DELETE | `/api/v1/documents`, `/{id}`, `/{id}/content`, `/{id}/download` | Document upload, metadata, content replace, download, delete |
| POST/GET | `/api/v1/documents/{id}/parse`, `/{id}/chunks`, `/{id}/embeddings` | Parse, chunk, and embed a document on demand |
| GET/POST | `/api/v1/ingestion-jobs`, `/{id}`, `/{id}/retry`, `/documents/{id}/ingestion-jobs` | Background ingestion jobs (list, inspect, retry failed) |
| POST | `/api/v1/rag/search`, `/rag/query`, `/rag/query/stream` | Hybrid retrieval and grounded RAG answers (`rag:query`) |
| GET/POST/PATCH/DELETE | `/api/v1/conversations`, `/{id}`, `/{id}/archive`, `/{id}/restore` | Conversation lifecycle (`chat:use`) |
| GET/POST/DELETE | `/api/v1/conversations/{id}/participants`, `/{user_id}` | Conversation participant management |
| POST | `/api/v1/conversations/{id}/messages`, `/messages/stream`, `/messages/{id}/cancel` | Send a chat message (sync or SSE stream) and cancel an in-flight stream |
| GET | `/api/v1/conversations/{id}/messages`, `/suggestions`, `/export` | List messages, follow-up suggestions, JSON/Markdown export |
| GET/PUT | `/api/v1/messages/{id}`, `/{id}/feedback` | Read a message and submit/update feedback |
| GET | `/api/v1/chat/analytics/overview` | Chat usage and quality analytics (`chat:manage`) |
| GET | `/api/v1/audit` | Query the append-only audit trail (`audit:read`) |
| GET | `/api/v1/admin/dashboard` | Org administration dashboard (`admin:dashboard`) |
| GET/POST | `/api/v1/admin/users`, `/users/{id}/activate\|deactivate` | Admin user list and activation (`admin:users`) |
| GET/PATCH | `/api/v1/admin/organizations/settings`, `/settings` | Quotas, defaults, feature overrides (`admin:organizations` / `admin:settings`) |
| PUT/DELETE | `/api/v1/admin/roles/{id}/permissions`, `/roles/{id}` | Custom role permission replace / archive (`admin:roles`) |
| GET | `/api/v1/admin/knowledge-spaces/{id}/stats` | Knowledge-space usage stats (`admin:knowledge_spaces`) |
| GET/POST | `/api/v1/admin/documents/overview`, `/bulk-reprocess`, `/bulk-delete` | Document ops (`admin:documents`) |
| GET/POST | `/api/v1/admin/ingestion/overview`, `/jobs/{id}/cancel` | Ingestion ops (`admin:ingestion`) |
| GET | `/api/v1/admin/audit/export` | Audit CSV/JSON export (`admin:audit`) |
| GET/POST | `/api/v1/admin/usage/*` | Usage trends, token cost, pricing, export (`admin:usage`) |
| CRUD | `/api/v1/admin/prompts`, `/activate`, `/deactivate`, `/rollback`, `/preview` | Prompt versioning (`admin:prompts`) |
| CRUD | `/api/v1/admin/llm-providers`, `/{id}/test` | LLM configs with masked secrets (`admin:llm`) |
| CRUD | `/api/v1/admin/feature-flags` | Feature flags with Redis cache (`admin:settings`) |
| GET | `/api/v1/admin/ops/overview` | Ops readiness + queue/LLM summary (`admin:ops`) |
| CRUD/POST | `/api/v1/admin/retention/policies`, `/retention/run` | Retention policies and runs (`admin:retention`) |

All endpoints above (except `/health/*` and `/system/info`) require
[development identity headers](#development-identity-headers) and are subject to
scoped RBAC.

Example system info capabilities (implemented in this commit vs. still planned):

```json
{
 "identity_context": true,
 "multi_tenancy": true,
 "rbac": true,
 "customers": true,
 "projects": true,
 "knowledge_spaces": true,
 "audit_log": true,
 "document_ingestion": true,
 "document_parsing": true,
 "document_chunking": true,
 "document_embeddings": true,
 "ingestion_workers": true,
 "rag": true,
 "chat": true,
 "multilingual_answers": true,
 "admin": true
}
```

## System roles & permissions summary

Permissions are namespaced `resource:action` strings; system roles are global (identical
across every organization) and cannot be created/modified through the API. Organizations can additionally define their
own custom roles with any subset of permissions via `POST /api/v1/roles`.

| System role | Summary |
| --- | --- |
| `platform_admin` | Bypasses every check; set directly on `User.is_platform_admin`, never assigned via the role API |
| `organization_admin` | Every permission below — full control of their organization |
| `project_manager` | Create/manage projects, knowledge spaces, and documents; read customers |
| `knowledge_manager` | Create/manage knowledge spaces and documents; read customers/projects |
| `developer` | Read-only: customers, projects, knowledge spaces; create/read/update documents (no delete) |
| `support_agent` | Read-only: customers, projects, knowledge spaces, documents |
| `viewer` | Read-only: customers, projects, knowledge spaces, documents |

| Permission | Meaning |
| --- | --- |
| `organization:read`, `organization:update`, `organization:manage_members` | Organization details and membership |
| `user:read`, `user:manage` | Users within a shared organization |
| `role:read`, `role:manage` | Custom roles and role assignments |
| `customer:create/read/update/archive` | Customers |
| `project:create/read/update/archive/manage_members` | Projects |
| `knowledge_space:create/read/update/archive/manage_members` | Knowledge spaces |
| `document:create/read/update/delete` | Documents |
| `rag:query` | Hybrid retrieval and grounded RAG answers |
| `chat:use` | Create/use conversations and send messages (granted to the same roles as `rag:query`) |
| `chat:manage` | Moderate any conversation and view chat analytics (`organization_admin`, `knowledge_manager`) |
| `admin:*` | Phase 4 governance (`dashboard`, `users`, `organizations`, `roles`, `knowledge_spaces`, `documents`, `ingestion`, `audit`, `usage`, `prompts`, `llm`, `settings`, `ops`, `retention`). Full set for `organization_admin`; knowledge managers get KS/documents/ingestion |
| `audit:read` | The audit trail |

Every user can always read/update their *own* profile (`GET`/`PATCH /users/{their own id}`)
without holding `user:read`/`user:manage`.

## Knowledge-space visibility

Knowledge spaces have two visibility levels:

* **`organization`** (default) — visible to anyone in the organization holding
 `knowledge_space:read`. No explicit grant needed.
* **`restricted`** — requires an *explicit* grant: either a knowledge-space-scoped role
 assignment, or a `KnowledgeSpaceMembership` row. Holding org-wide `knowledge_space:read`
 is **not** sufficient — even the organization admin who created a restricted space gets
 `404` (not `403`) without an explicit grant, so a caller can never distinguish "exists
 but restricted" from "does not exist" (see
 `tests/security/test_restricted_knowledge_space_access.py`).
* `platform_admin` bypasses both rules.

## Example curl commands

```bash
# Seed a local dev tenant and capture the printed admin headers.
make bootstrap-dev

USER_ID="<admin uuid printed above>"
ORG_ID="<org uuid printed above>"

# System info (no auth required).
curl -s http://localhost:8000/api/v1/system/info | jq

# List organizations the admin is a member of.
curl -s http://localhost:8000/api/v1/organizations \
 -H "X-ContextForge-User-ID: $USER_ID" \
 -H "X-ContextForge-Organization-ID: $ORG_ID" | jq

# Create a customer as the organization admin.
curl -s -X POST http://localhost:8000/api/v1/customers \
 -H "X-ContextForge-User-ID: $USER_ID" \
 -H "X-ContextForge-Organization-ID: $ORG_ID" \
 -H "Content-Type: application/json" \
 -d '{"name": "Acme Corp", "code": "ACME"}' | jq

# Missing identity headers -> 401.
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/customers
```

## Auth roadmap

Development identity is an interim
mechanism only. Planned follow-ups, in rough order:

1. Real authentication (OIDC/SSO) replacing header-based identity, without changing
 `RequestContext` or any application service's signature.
2. Session/token issuance and refresh flows.
3. Per-organization identity provider configuration (enterprise SSO).
4. Service-to-service / API-key authentication for automation clients.
5. Removing development identity from non-production builds entirely once (1)–(2) ship.

See [Planned roadmap](#planned-roadmap) below for the rest of the product roadmap.

## Health-check behavior

* `/health/live` always checks process liveness only.
* `/health/ready` probes dependencies concurrently with timeouts.
* Any mandatory dependency down → HTTP 503 and `"status": "not_ready"`.
* Responses never include credentials or stack traces.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Ready returns 503 | Dependency not healthy | `docker compose ps` and inspect service logs |
| Migrations fail | Postgres not ready | Ensure `postgres` is healthy, rerun `make migrate` |
| MinIO check fails | Bucket missing | Ensure `minio-init` completed successfully |
| Docs missing in prod | Expected | Docs disabled when `CONTEXTFORGE_APP_ENVIRONMENT=production` |

## Security notes

* Do not commit `.env` or secrets.
* Containers run as non-root (`uid 10001`).
* CORS is off unless origins are explicitly configured.
* **Development identity is not production authentication** — it is unconditionally
 disabled in `staging`/`production` (see [Development identity headers](#development-identity-headers)). Real authentication (OIDC/SSO)
 is tracked in the [Auth roadmap](#auth-roadmap) and has not shipped yet — treat any
 non-production deployment of this API as an internal foundation only.
* Authorization (RBAC + tenancy) is enforced server-side only; no client-supplied
 role/permission header is ever trusted.
* Audit metadata is sanitized to strip secret-like keys before persistence.

## Development conventions

* English for code, comments, docs, logs, and commits
* UTC timestamps in the backend
* User-facing timezone conversion will be handled at presentation boundaries later
* No LangChain/LangGraph/LLM SDKs in this foundation commit

## Planned roadmap

1. ~~Multi-tenancy, scoped RBAC, and audit logging~~ — done (development identity only;
 see [Auth roadmap](#auth-roadmap) for real authentication)
2. ~~Document upload, parsing, chunking, embeddings, and ingestion workers~~ — done
3. ~~Hybrid retrieval, reranking, and RAG answering~~ — done
4. ~~Multilingual chat experience (Turkish / English) with session memory~~ — done
5. ~~Administration & governance~~ — done (Phase 4)
6. ~~Production engineering (Docker/Helm/Terraform, observability, CI/CD, DR)~~ — done
   (Phase 5)
7. Real authentication (OIDC/SSO) replacing development identity
8. Deeper admin UX and org-level SSO configuration

## License

MIT — see [LICENSE](LICENSE).

## Author

Built by [serencarikci](https://github.com/serencarikci).



## Phase 4 — Administration & Governance

Phase 4 adds organization administration under `/api/v1/admin/*` with dedicated
`admin:*` permissions. Organization admins receive the full set; knowledge managers
receive knowledge-space/document/ingestion admin permissions.

### Admin capabilities

| Area | Endpoints (prefix `/api/v1/admin`) |
| --- | --- |
| Dashboard | `GET /dashboard` |
| Users | `GET /users`, activate/deactivate |
| Org settings | `GET|PATCH /organizations/settings`, `GET|PATCH /settings` |
| Roles | `PUT /roles/{id}/permissions`, `DELETE /roles/{id}` |
| Knowledge spaces | `GET /knowledge-spaces/{id}/stats` |
| Documents | `GET /documents/overview`, bulk reprocess/delete |
| Ingestion | `GET /ingestion/overview`, cancel pending jobs |
| Audit | `GET /audit/export?format=json|csv` |
| Usage / tokens | overview, trends, tokens, pricing, export |
| Prompts | CRUD + activate/deactivate/preview |
| LLM providers | CRUD + connectivity test (API keys masked) |
| Feature flags | CRUD + resolved map (cached) |
| Ops | `GET /ops/overview` |
| Retention | policies CRUD + `POST /retention/run` |

```mermaid
flowchart TD
  Admin[Organization Admin] --> API["/api/v1/admin"]
  API --> Services[Admin services]
  Services --> DB[(Postgres admin + tenant tables)]
  Services --> Redis[(Feature-flag cache)]
  Worker[contextforge-retention-worker] --> Retention[RetentionCleanupService]
  Retention --> DB
```

### Admin environment

```bash
CONTEXTFORGE_ADMIN_RETENTION_ENABLED=true
CONTEXTFORGE_ADMIN_RETENTION_BATCH_SIZE=500
CONTEXTFORGE_ADMIN_RETENTION_DEFAULT_DAYS=365
CONTEXTFORGE_ADMIN_RETENTION_WORKER_INTERVAL_SECONDS=3600.0
CONTEXTFORGE_ADMIN_CACHE_TTL_SECONDS=30
CONTEXTFORGE_ADMIN_TOKEN_USAGE_ROLLUP_ENABLED=true
CONTEXTFORGE_ADMIN_TOKEN_PRICING_CURRENCY=USD
CONTEXTFORGE_ADMIN_LLM_TEST_TIMEOUT_SECONDS=5.0
```

## Phase 5 — Production Engineering

Phase 5 hardens operations without rewriting Phase 1–4 product features. Version
**0.5.0** ships security headers, rate limiting, Prometheus metrics, retention worker
in Compose, Helm/Terraform deploy stubs, CD, backups, load tests, and runbooks.

```mermaid
flowchart TB
  Dev[Developer / CI] --> GHCR[GHCR image]
  GHCR --> Helm[Helm chart]
  Helm --> API[API Deployment]
  Helm --> Ingest[Ingestion Worker]
  Helm --> Retain[Retention Worker]
  API --> Prom[Prometheus /metrics]
  Prom --> Graf[Grafana dashboards]
  API --> PG[(Postgres)]
  API --> Redis[(Redis)]
  Cron[Backup CronJobs] --> PG
  Cron --> MinIO[(Object storage)]
  Cron --> Qdrant[(Qdrant)]
```

### Docker & Compose

| Artifact | Purpose |
| --- | --- |
| `Dockerfile` | Multi-stage, non-root, OCI labels, `STOPSIGNAL`, worker-friendly healthcheck skip via `CONTEXTFORGE_SKIP_HEALTHCHECK` |
| `docker-compose.yml` | Dev stack + `retention-worker` + optional `--profile obs` (Prometheus/Grafana/Loki) |
| `docker-compose.prod.yml` | Resource limits, `env_file: .env`, restart policies, no unnecessary host binds |
| `docker-compose.obs.yml` | Observability overlay (same profile) |

```bash
docker compose config
docker compose -f docker-compose.yml -f docker-compose.prod.yml config
docker compose --profile obs up -d
make compose-prod-config
```

### App hardening

* Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
  `Permissions-Policy`; HSTS when not `local`/`test`/`development`
* Rate limit: sliding window for `/api/v1` (`memory` or `redis`), health paths excluded
* Metrics: `GET /metrics` (Prometheus text) with request counters, latency histogram,
  dependency-up gauges

```bash
CONTEXTFORGE_RATE_LIMIT_ENABLED=true
CONTEXTFORGE_RATE_LIMIT_REQUESTS=120
CONTEXTFORGE_RATE_LIMIT_WINDOW_SECONDS=60
CONTEXTFORGE_RATE_LIMIT_BACKEND=memory
CONTEXTFORGE_OBSERVABILITY_METRICS_ENABLED=true
CONTEXTFORGE_OBSERVABILITY_METRICS_PATH=/metrics
```

### Helm

Chart: `deploy/helm/contextforge/` with values for dev/staging/prod. Templates cover
namespace, SA, ConfigMap, ExternalSecret stub, API/ingestion/retention Deployments,
migrate Job, Service, Ingress, HPA, PDB, NetworkPolicy, optional ServiceMonitor,
and backup CronJob.

```bash
make helm-lint
# or
./scripts/validate-helm.sh
```

### Terraform

Provider-neutral stubs under `deploy/terraform/modules/` (`networking`, `kubernetes`,
`postgres`, `redis`, `object_storage`, `dns`) composed by
`deploy/terraform/environments/{staging,production}`.

```bash
make terraform-validate
# or
./scripts/validate-terraform.sh
cd deploy/terraform/environments/staging
terraform init -backend=false
terraform validate
```

Wire real cloud providers in forks; modules intentionally avoid vendor lock-in.

### CI/CD

| Workflow | Trigger | What it does |
| --- | --- | --- |
| `.github/workflows/ci.yml` | push/PR | lint, mypy, unit/arch, migration SQL check, helm/terraform, secret scan, SBOM soft-fail, docker build |
| `.github/workflows/cd.yml` | `v*` tag / dispatch | build/push GHCR, staging deploy render + smoke, production environment (approval) |
| `.github/workflows/release.yml` | `v*` tag | changelog stub + GitHub Release |

Default workflow permissions are least-privilege (`contents: read` unless release needs write).

### Secrets

* Never commit `.env` or live credentials
* Example ExternalSecret: `deploy/secrets/external-secrets.example.yaml`
* Helm references `existingSecret` / External Secrets only (no secret values in values files)
* Rotation: update secret manager → refresh ExternalSecret → restart API/workers — see
  `ops/runbooks/secret-compromise.md`

### Observability & SLOs

Configs live under `deploy/observability/`. Scrape `api:8000/metrics`, alert rules include
`severity`, `description`, and `runbook_url` labels. Grafana dashboard:
`contextforge-overview.json`.

| SLO (initial goals — not claimed achieved) | Target |
| --- | --- |
| Availability (monthly) | 99.9% |
| API readiness success | 99.5% |
| HTTP request success (non-5xx) | 99.0% |
| Latency p95 (read paths) | < 1.0s |
| Latency p95 (RAG/chat) | < 5.0s |
| Backup success rate | 99% |

### Backup / DR

Scripts: `scripts/backup/backup_postgres.sh`, `backup_minio.sh`, `backup_qdrant.sh`,
`restore_postgres.sh`, `verify_backup.sh`. CronJob examples under
`deploy/k8s/cronjobs/` and Helm `backupCronJob`.

| DR goal (documented targets) | Value |
| --- | --- |
| RPO | ≤ 24h (daily backups) |
| RTO | ≤ 4h (restore + verify + cutover) |

### Load testing

k6 scenarios (document thresholds in scripts; requires `k6` installed):

```bash
make load-test-smoke
k6 run perf/k6/load_chat.js
k6 run perf/k6/load_rag.js
```

### Ops runbooks

Concise runbooks under `ops/runbooks/`: deploy-failure, api-outage, postgres-outage,
redis-outage, queue-backlog, llm-outage, rollback, backup-restore, secret-compromise.
Production checklist: `ops/production-readiness-checklist.md`.

### Makefile targets (Phase 5)

```bash
make validate-infra
make helm-lint
make terraform-validate
make backup-postgres
make load-test-smoke
make compose-prod-config
```
