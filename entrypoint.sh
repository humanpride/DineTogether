#!/bin/sh

set -e

while ! nc -z "$POSTGRES_SERVER" "$POSTGRES_PORT"; do
  echo "Waiting for postgres to start..."
  sleep 3
done
echo 'Postgres started'

mkdir -p /app/media
echo '[startup] Applying database migrations: alembic upgrade head'
if alembic upgrade head; then
  echo '[startup] Database migrations completed successfully.'
else
  migration_status=$?
  echo "[startup] ERROR: Database migration failed (exit code $migration_status)." >&2
  echo '[startup] See the Alembic/SQLAlchemy output above for the failing migration and database error.' >&2
  echo '[startup] Aborting startup: the Celery worker and API will not be started.' >&2
  exit "$migration_status"
fi

celery --app core.celery_app worker --pool threads --loglevel INFO &

exec uvicorn main:app --host 0.0.0.0 --port 8000
