#!/bin/bash
# Build script for Railway deployment
# Railway will auto-detect Node.js from package.json and Python from runtime.txt

set -e  # Exit on error

echo "=== Environment Check ==="
echo "Node version: $(node --version 2>/dev/null || echo 'Node not found')"
echo "NPM version: $(npm --version 2>/dev/null || echo 'NPM not found')"
echo "Python version: $(python3 --version 2>/dev/null || echo 'Python not found')"
echo "Pip version: $(pip3 --version 2>/dev/null || echo 'Pip not found')"

echo ""
echo "=== Building frontend ==="
cd frontend

echo "Installing frontend dependencies..."
npm install

echo "Building React app..."
npm run build

echo "Checking build output..."
if [ -d "dist" ]; then
    echo "✅ Frontend build successful!"
    if [ -f "dist/index.html" ]; then
        echo "✅ index.html found"
    else
        echo "❌ index.html NOT found!"
        exit 1
    fi
else
    echo "❌ dist/ directory not created!"
    exit 1
fi

cd ..
echo "=== Frontend build complete ==="

echo ""
echo "=== Installing backend dependencies ==="
# Use pip3 if available, fallback to pip
if command -v pip3 &> /dev/null; then
    pip3 install -r backend/requirements.txt
elif command -v pip &> /dev/null; then
    pip install -r backend/requirements.txt
else
    echo "❌ Neither pip3 nor pip found!"
    exit 1
fi

echo "=== Build complete ==="
