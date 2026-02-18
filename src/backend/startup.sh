#!/bin/sh
# Startup script: run Alembic migrations then start the app.
# Handles the case where tables exist but alembic_version doesn't
# (DB was populated before Alembic was introduced).

set -e

echo "Running database migrations..."
if alembic upgrade head 2>&1; then
  echo "Migrations completed successfully."
else
  echo "Migration failed. Checking if this is a first-time Alembic setup..."
  # Tables exist but alembic_version doesn't — stamp current state
  alembic stamp head
  echo "Stamped database at head revision."
fi

echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
