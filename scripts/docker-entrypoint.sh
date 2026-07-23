#!/bin/sh
set -eu

# Entrypoint for API and migration containers.
# Migration mode: CONTEXTFORGE_RUN_MIGRATIONS=true

if [ "${CONTEXTFORGE_RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "Running database migrations..."
  alembic upgrade head
  echo "Migrations complete."
  exit 0
fi

exec "$@"
