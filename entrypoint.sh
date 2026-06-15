#!/bin/bash

while ! nc -z $POSTGRES_SERVER $POSTGRES_PORT; do
  echo "Waiting for postgres to start..."
  sleep 3
done
echo 'Postgres started'

mkdir -p /app/media
alembic upgrade head

celery --app core.celery_app worker --pool threads --loglevel INFO &

celery --app core.celery_app flower \
  --port=5555 \
  --url-prefix=flower \
  --broker-api=http://$RABBIT_USER:$RABBIT_USER_PASS@rabbitmq:15672/api/ &

exec uvicorn main:app --host 0.0.0.0 --port 8000
