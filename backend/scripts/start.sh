#!/bin/sh
set -eu

alembic upgrade head
python -m scripts.bootstrap_admin

exec uvicorn app.application:app --host 0.0.0.0 --port "${PORT:-8000}"
