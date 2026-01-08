#!/bin/bash

# Start the Electron app in development mode
# This starts both the backend and the frontend with Electron

cd "$(dirname "$0")"

echo "Starting Face Classifier in development mode..."
echo ""

# Check if backend is running
if ! curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "Backend is not running. Starting backend..."
    cd backend
    uv run uvicorn main:app --host 127.0.0.1 --port 8000 &
    BACKEND_PID=$!
    cd ..
    
    # Wait for backend to be ready
    echo "Waiting for backend to start..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
            echo "Backend is ready!"
            break
        fi
        sleep 1
    done
else
    echo "Backend already running."
    BACKEND_PID=""
fi

# Start the Electron app
cd frontend
bun run dev:electron

# Cleanup backend if we started it
if [ ! -z "$BACKEND_PID" ]; then
    echo "Stopping backend..."
    kill $BACKEND_PID 2>/dev/null
fi
