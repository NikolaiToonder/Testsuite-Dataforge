#!/bin/bash

APP_PATH="/home/thomas/bachelor/dataforge"

# Start backend
echo "Starting backend..."
cd "$APP_PATH/backend"
source .venv/bin/activate
uvicorn main:app --reload &
BACKEND_PID=$!
cd ..

# Start frontend
echo "Starting frontend..."
cd "$APP_PATH/frontend"
yarn dev &
FRONTEND_PID=$!
cd ..

# Wait for services
echo "Waiting for services to be ready..."
sleep 5

echo "Environment ready!"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"

# Cleanup on exit
trap "echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID; docker compose down" EXIT

wait