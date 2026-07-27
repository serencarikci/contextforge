# Backup and restore

## Backup
```bash
POSTGRES_HOST=... POSTGRES_USER=... POSTGRES_DB=contextforge POSTGRES_PASSWORD=... \
  ./scripts/backup/backup_postgres.sh
./scripts/backup/verify_backup.sh
```

## Restore (Postgres)
```bash
BACKUP_FILE=./backups/postgres/contextforge-....sql.gz \
POSTGRES_HOST=... POSTGRES_USER=... POSTGRES_DB=contextforge POSTGRES_PASSWORD=... \
  ./scripts/backup/restore_postgres.sh
```

Also back up MinIO (`backup_minio.sh`) and Qdrant snapshots (`backup_qdrant.sh`).
