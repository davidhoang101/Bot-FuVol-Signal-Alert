#!/bin/bash
# Build script for Railway deployment

echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "Frontend build complete. Files in frontend/dist/"
