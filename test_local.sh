#!/bin/bash
# Quick test script to verify local setup

echo "=== Testing Local Setup ==="
echo ""

# Check if frontend is built
echo "1. Checking frontend build..."
if [ -d "frontend/dist" ] && [ -f "frontend/dist/index.html" ]; then
    echo "✅ Frontend is built"
else
    echo "⚠️ Frontend not built. Run: cd frontend && npm install && npm run build"
fi

# Check if backend venv exists
echo ""
echo "2. Checking backend setup..."
if [ -d "backend/venv" ]; then
    echo "✅ Backend venv exists"
else
    echo "⚠️ Backend venv not found. Run: cd backend && python3 -m venv venv"
fi

# Check Python dependencies
echo ""
echo "3. Testing Python imports..."
cd backend
if [ -d "venv" ]; then
    source venv/bin/activate
    python3 -c "from app.main import app; print('✅ Backend imports OK')" 2>&1
    deactivate
else
    echo "⚠️ Skipping import test (venv not found)"
fi
cd ..

# Check config
echo ""
echo "4. Checking config files..."
if [ -f "config.yaml" ]; then
    echo "✅ config.yaml exists"
else
    echo "⚠️ config.yaml not found"
fi

if [ -f ".env" ]; then
    echo "✅ .env exists"
else
    echo "⚠️ .env not found (create from env.example.txt if needed)"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To run the app:"
echo "  ./run_local_web.sh"
echo ""
echo "Or manually:"
echo "  1. cd frontend && npm run build"
echo "  2. cd ../backend && source venv/bin/activate"
echo "  3. python -m app.main"
echo ""

