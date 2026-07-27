#!/usr/bin/env bash
set -euo pipefail

: "${BACKUP_FILE:?BACKUP_FILE is required}"

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "Missing backup file: ${BACKUP_FILE}" >&2
  exit 1
fi

SIZE="$(wc -c < "${BACKUP_FILE}" | tr -d ' ')"
if [ "${SIZE}" -lt 64 ]; then
  echo "Backup file too small (${SIZE} bytes)" >&2
  exit 1
fi

case "${BACKUP_FILE}" in
  *.sql.gz)
    gzip -t "${BACKUP_FILE}"
    ;;
  *.snapshot|*.gz|*.tar)
    ;;
  *)
    echo "Unknown backup extension; size check only"
    ;;
esac

echo "Backup OK: ${BACKUP_FILE} (${SIZE} bytes)"
