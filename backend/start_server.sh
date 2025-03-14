#!/usr/bin/env bash
# For starting the server on Cloud Run
# Set default values for WORKERS and PORT
WORKERS=${WORKERS:-1}
PORT=${PORT:-8080}
uvicorn app.main:app --port $PORT --host 0.0.0.0 --workers $WORKERS
