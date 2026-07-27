# LLM outage

## Symptoms
- RAG/chat answers fail or time out; admin LLM connectivity test fails.

## Checks
1. Provider status page / credentials.
2. `CONTEXTFORGE_LLM_*` settings and admin LLM configs.
3. Timeout and retry metrics in logs.

## Mitigation
1. Switch to a healthy provider/config via admin LLM settings.
2. Temporarily enable mock provider only in non-production.
3. Communicate degraded answer quality to stakeholders.
