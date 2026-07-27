#!/bin/sh
set -eu

if [ "${CONTEXTFORGE_SKIP_HEALTHCHECK:-false}" = "true" ]; then
  exit 0
fi

curl -fsS "http://127.0.0.1:${CONTEXTFORGE_API_PORT:-8000}/api/v1/health/live" >/dev/null
