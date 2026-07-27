# Queue backlog

## Symptoms
- Rising Redis ingestion queue length; delayed document processing.

## Checks
1. Admin ops / ingestion overview.
2. Ingestion worker replica count and error logs.
3. Downstream Qdrant/MinIO health.

## Mitigation
1. Scale ingestion workers.
2. Fix poison messages / failed jobs.
3. Pause uploads if storage is saturated.
