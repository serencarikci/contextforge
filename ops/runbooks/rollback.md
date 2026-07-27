# Rollback

## When
- Bad release, rising 5xx after deploy, or failed smoke checks.

## Steps
1. Identify last known-good image tag / Helm revision.
2. `helm rollback contextforge <revision>` or redeploy previous tag via CD.
3. Confirm `/health/live` and `/health/ready`.
4. Watch error rate for 15 minutes.
