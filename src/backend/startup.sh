#!/bin/sh
# Startup script: run Alembic migrations then start the app.
# Handles the case where tables exist but alembic_version doesn't
# (DB was populated before Alembic was introduced).

set -e

echo "Running database migrations..."
if alembic upgrade head 2>&1; then
  echo "Migrations completed successfully."
else
  # Check if this is the specific "no alembic_version table" case
  if alembic current 2>&1 | grep -q "alembic_version"; then
    # alembic_version table exists — this is a real migration failure
    echo "FATAL: Migration failed (alembic_version table exists). Exiting."
    exit 1
  fi
  # No alembic_version table — first-time Alembic setup on existing DB
  echo "First-time Alembic setup. Stamping database at head..."
  alembic stamp head
  echo "Stamped database at head revision."
fi

echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
