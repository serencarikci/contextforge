#!/usr/bin/env bash
set -euo pipefail

: "${POSTGRES_HOST:?POSTGRES_HOST is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${BACKUP_FILE:?BACKUP_FILE is required (path to .sql.gz)}"

export PGPASSWORD="${POSTGRES_PASSWORD:-}"
gunzip -c "${BACKUP_FILE}" | psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"
echo "Restored ${BACKUP_FILE} into ${POSTGRES_DB}"
