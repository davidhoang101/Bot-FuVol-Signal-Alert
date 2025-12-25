#!/bin/bash
# Run web app locally (like production on Railway)

set -e

echo "=== Building Frontend ==="
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Build frontend
echo "Building React app..."
npm run build

if [ ! -d "dist" ] || [ ! -f "dist/index.html" ]; then
    echo "❌ Frontend build failed!"
    exit 1
fi

echo "✅ Frontend built successfully"
cd ..

echo ""
echo "=== Setting up Backend ==="
cd backend

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo "Installing backend dependencies..."
pip install -q -r requirements.txt
pip install -q -r ../requirements.txt

echo ""
echo "=== Starting Backend Server ==="
echo "Backend will serve frontend from: ../frontend/dist"
echo "API: http://localhost:8000/api"
echo "Frontend: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run backend
python -m app.main

