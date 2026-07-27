# Redis outage

## Symptoms
- Ready fails on redis; ingestion queue stalls; rate-limit backend errors.

## Checks
1. Redis ping / memory / AOF status.
2. API falls back to in-memory rate limiting when Redis backend errors.

## Mitigation
1. Restart Redis or fail over.
2. Temporarily set `CONTEXTFORGE_RATE_LIMIT_BACKEND=memory` if needed.
3. Drain/replay ingestion backlog after recovery.
