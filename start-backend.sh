#!/bin/bash
# Start the backend server
cd "$(dirname "$0")/backend"
~/.local/bin/uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
