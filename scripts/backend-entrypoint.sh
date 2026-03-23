#!/usr/bin/env sh
set -e

MAX_ATTEMPTS="${DB_WAIT_MAX_ATTEMPTS:-30}"
SLEEP_SECONDS="${DB_WAIT_SLEEP_SECONDS:-2}"
ATTEMPT=1

echo "Running Alembic migrations (with retry)..."
until alembic upgrade head
do
  if [ "$ATTEMPT" -ge "$MAX_ATTEMPTS" ]; then
    echo "Migration failed after ${MAX_ATTEMPTS} attempts."
    exit 1
  fi
  echo "Database unavailable, retry ${ATTEMPT}/${MAX_ATTEMPTS} in ${SLEEP_SECONDS}s..."
  ATTEMPT=$((ATTEMPT + 1))
  sleep "$SLEEP_SECONDS"
done

echo "Starting FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
