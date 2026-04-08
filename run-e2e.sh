#!/bin/bash

COMPOSE_FILE="docker-compose.test.yml"
APP_PATH="/home/thomas/bachelor/dataforge"

set -e  # exit on error

echo "Starting E2E environment..."

# 1. Start database
echo "Starting database..."
docker compose -f "$COMPOSE_FILE" down -v
docker compose -f "$COMPOSE_FILE" up -d

# 2. Wait for DB to be ready
echo "Waiting for database..."
sleep 5

# 3. Set DB connection string
export DATABASE_URL="postgresql://test_user:test_password@localhost:5433/dataforge_test"

# 4. Start backend
echo "Starting backend..."
cd "$APP_PATH/backend"
source .venv/bin/activate
uvicorn main:app --reload &
BACKEND_PID=$!
cd ..

# 5. Start frontend
echo "Starting frontend..."
cd "$APP_PATH/frontend"
yarn dev &
FRONTEND_PID=$!
cd ..

# 6. Wait for services
echo "Waiting for services to be ready..."
sleep 5

echo "Environment ready!"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"

# 8. Cleanup on exit
trap "echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID; docker compose down" EXIT

wait