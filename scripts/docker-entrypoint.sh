#!/bin/sh
set -eu


if [ "${CONTEXTFORGE_RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "Running database migrations..."
  alembic upgrade head
  echo "Migrations complete."
  exit 0
fi

exec "$@"
