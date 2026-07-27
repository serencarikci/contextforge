# API outage

## Symptoms
- `/api/v1/health/live` or `/ready` failing; elevated 5xx; scrape target down.

## Checks
1. `curl -fsS https://<host>/api/v1/health/live`
2. `curl -fsS https://<host>/api/v1/health/ready`
3. Pod events/logs for API deployment.
4. Grafana: ContextForge Overview — error rate and dependency gauges.

## Mitigation
1. Scale API replicas if capacity-related.
2. Restore down dependency (Postgres/Redis/Qdrant/MinIO).
3. Roll back recent deploy if regression suspected.
