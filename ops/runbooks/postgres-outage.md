# Postgres outage

## Symptoms
- Ready check fails on postgres; API 503; migrations blocked.

## Checks
1. Database endpoint connectivity and disk usage.
2. Connection pool saturation in API logs.
3. Recent schema migrations.

## Mitigation
1. Fail over / restart primary if infrastructure allows.
2. Restore from latest verified backup if data loss (see backup-restore).
3. Document incident timeline and RPO impact.
