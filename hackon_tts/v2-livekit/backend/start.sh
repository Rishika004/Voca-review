#!/usr/bin/env bash
# Runs both the token server and the LiveKit agent worker in one Render service.
set -e

# Agent worker in the background (registers with LiveKit Cloud)
python agent.py start &

# Token/API server in the foreground on Render's assigned port
exec uvicorn server:app --host 0.0.0.0 --port "${PORT:-8001}"
