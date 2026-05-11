#!/usr/bin/env bash
set -euo pipefail

APP_PATH="../dataforge"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo "Stopping frontend/backend..."

  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi

  if [[ -n "${FRONTEND_PID:-}" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi

  wait "$BACKEND_PID" 2>/dev/null || true
  wait "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

# Start backend silently
echo "Starting backend..."
cd "$APP_PATH/backend"
source .venv/bin/activate
uvicorn main:app --reload &>/dev/null &
BACKEND_PID=$!
cd ..

# Start frontend silently
echo "Starting frontend..."
cd frontend
yarn dev &>/dev/null &
FRONTEND_PID=$!
cd ..

# Wait for services
echo "Waiting for services to be ready..."
sleep 5

echo "Environment ready."

# Run tests and show only test output
cd "../Testsuite-Dataforge/frontend"

set +e
npm run test:e2e
TEST_EXIT_CODE=$?
set -e

exit "$TEST_EXIT_CODE"