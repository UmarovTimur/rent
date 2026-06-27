#!/bin/sh
set -e

alembic upgrade head

#uvicorn src.server.app:create_application --factory --host 0.0.0.0 --port 8000
python3 -m src
