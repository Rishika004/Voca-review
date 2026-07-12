#!/usr/bin/env bash
set -e
python agent.py start &
exec uvicorn server:app --host 0.0.0.0 --port "${PORT:-8002}"
