# Production readiness checklist

- [ ] Image built from tagged release (`v0.5.x`) and scanned
- [ ] Migrations applied successfully (Helm migrate Job / Alembic)
- [ ] Secrets sourced from secret manager (External Secrets), not git
- [ ] `CONTEXTFORGE_APP_ENVIRONMENT=production` and docs disabled
- [ ] Rate limiting enabled (`redis` backend preferred)
- [ ] `/metrics` scraped; Grafana dashboard imported; alerts wired
- [ ] Ingress TLS enabled; HSTS expected behind HTTPS
- [ ] HPA + PDB configured for API
- [ ] NetworkPolicy enabled in production values
- [ ] Backup CronJobs scheduled; restore drill documented
- [ ] Runbooks reviewed by on-call
- [ ] Smoke: `curl` live + ready after deploy
- [ ] Load smoke (`perf/k6/smoke.js`) against staging
