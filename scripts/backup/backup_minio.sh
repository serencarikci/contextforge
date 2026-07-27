#!/usr/bin/env bash
set -euo pipefail

: "${MINIO_ENDPOINT:?MINIO_ENDPOINT is required}"
: "${MINIO_ACCESS_KEY:?MINIO_ACCESS_KEY is required}"
: "${MINIO_SECRET_KEY:?MINIO_SECRET_KEY is required}"
: "${MINIO_BUCKET:?MINIO_BUCKET is required}"
: "${BACKUP_DIR:=./backups/minio}"

mkdir -p "${BACKUP_DIR}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${BACKUP_DIR}/${MINIO_BUCKET}-${STAMP}"

mc alias set cfbackup "${MINIO_ENDPOINT}" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}" >/dev/null
mc mirror "cfbackup/${MINIO_BUCKET}" "${OUT}"
echo "Mirrored bucket to ${OUT}"
