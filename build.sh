#!/bin/bash
# Build script for Railway deployment
# Railway will auto-detect Node.js from package.json

set -e  # Exit on error

echo "=== Building frontend ==="
echo "Node version: $(node --version)"
echo "NPM version: $(npm --version)"

cd frontend

echo "Installing dependencies..."
npm install

echo "Building React app..."
npm run build

echo "Checking build output..."
if [ -d "dist" ]; then
    echo "✅ Frontend build successful!"
    echo "Files in dist/:"
    ls -la dist/ | head -10
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
