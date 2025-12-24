#!/bin/bash
set -e

echo "=== Starting Application ==="
echo "PORT: ${PORT:-8000}"
echo "PYTHONPATH: ${PYTHONPATH:-not set}"
echo "Working directory: $(pwd)"
echo "Python version: $(python3 --version)"

# Set PYTHONPATH to include /app for imports
export PYTHONPATH=/app:${PYTHONPATH}

# Check if frontend exists
if [ -d "/app/frontend/dist" ]; then
    echo "✅ Frontend dist found at /app/frontend/dist"
    ls -la /app/frontend/dist | head -10
else
    echo "⚠️ Frontend dist not found at /app/frontend/dist"
fi

# Check if backend exists
if [ -d "/app/backend" ]; then
    echo "✅ Backend found at /app/backend"
else
    echo "❌ Backend not found at /app/backend"
    exit 1
fi

# Start the application
echo "Starting uvicorn on port ${PORT:-8000}..."
cd /app/backend
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info

