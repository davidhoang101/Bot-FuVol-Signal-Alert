#!/bin/bash
# Build script for Railway deployment

set -e  # Exit on error

echo "=== Building frontend ==="
cd frontend

echo "Installing dependencies..."
npm install

echo "Building React app..."
npm run build

echo "Checking build output..."
if [ -d "dist" ]; then
    echo "✅ Frontend build successful!"
    echo "Files in dist/:"
    ls -la dist/
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
