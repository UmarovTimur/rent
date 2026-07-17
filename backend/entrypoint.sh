#!/bin/sh
set -e

alembic upgrade head

# Honour an explicit command override (e.g. the celery service's `command:` in
# docker-compose.yml) — without this, ENTRYPOINT always ran the FastAPI app
# regardless of `command:`, so the celery container silently ran the backend
# server instead of the worker/beat, and none of the scheduled tasks ever fired.
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

exec python3 -m src
