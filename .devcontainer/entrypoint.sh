#!/bin/bash

set -e

while ! nc -z "$POSTGRES_SERVER" "$POSTGRES_PORT"; do
  echo "Waiting for postgres to start..."
  sleep 3
done
echo "✓ Postgres started"

cd /workspace/src

echo "Applying database migrations..."
uv run alembic upgrade head
echo "✓ Migrations applied"

exec "$@"
