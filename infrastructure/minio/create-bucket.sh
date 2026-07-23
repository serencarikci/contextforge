#!/bin/sh
set -eu

MC_ALIAS="local"
ENDPOINT="${MINIO_ENDPOINT:-http://minio:9000}"
ACCESS_KEY="${MINIO_ROOT_USER:-contextforge_minio}"
SECRET_KEY="${MINIO_ROOT_PASSWORD:-contextforge_minio_secret}"
BUCKET="${MINIO_BUCKET:-contextforge-documents}"

echo "Configuring MinIO client alias..."
mc alias set "${MC_ALIAS}" "${ENDPOINT}" "${ACCESS_KEY}" "${SECRET_KEY}"

echo "Ensuring bucket exists: ${BUCKET}"
mc mb --ignore-existing "${MC_ALIAS}/${BUCKET}"

echo "MinIO bucket initialization complete."
