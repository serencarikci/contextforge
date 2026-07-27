#!/usr/bin/env bash
set -euo pipefail

: "${QDRANT_URL:?QDRANT_URL is required}"
: "${BACKUP_DIR:=./backups/qdrant}"
COLLECTION="${QDRANT_COLLECTION_NAME:-document_chunks}"

mkdir -p "${BACKUP_DIR}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${BACKUP_DIR}/${COLLECTION}-${STAMP}.snapshot"

SNAP_NAME="$(curl -fsS -X POST "${QDRANT_URL}/collections/${COLLECTION}/snapshots" | sed -n 's/.*"name":"\([^"]*\)".*/\1/p')"
if [ -z "${SNAP_NAME}" ]; then
  echo "Failed to create Qdrant snapshot" >&2
  exit 1
fi
curl -fsS "${QDRANT_URL}/collections/${COLLECTION}/snapshots/${SNAP_NAME}" -o "${OUT}"
echo "Wrote ${OUT}"
