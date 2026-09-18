#!/usr/bin/env bash
set -e

echo "Starting Smart Campus Energy Optimization Platform..."

# Start backend in background
(cd backend && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000) &
BACKEND_PID=$!

# Start frontend
(cd frontend && npm run dev) &
FRONTEND_PID=$!

trap "echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID" EXIT INT TERM

wait
