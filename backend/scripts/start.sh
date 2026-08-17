#!/bin/sh
set -eu

alembic upgrade head
python scripts/bootstrap_admin.py

exec uvicorn app.application:app --host 0.0.0.0 --port "${PORT:-8000}"
