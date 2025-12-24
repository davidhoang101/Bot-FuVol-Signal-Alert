# Quick Setup Guide

## Step-by-Step Setup

### 1. Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Go back to root
cd ..
```

### 2. Create Configuration Files

```bash
# Create .env file (copy from example)
cat > .env << EOF
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
BINANCE_ENABLE_TESTNET=true
DEBUG=false
LOG_LEVEL=INFO
EOF

# config.yaml should already exist with defaults
```

### 3. Initialize Database

```bash
cd backend
python -c "from app.db.session import init_db; import asyncio; asyncio.run(init_db())"
cd ..
```

### 4. Start Backend

```bash
cd backend
python -m app.main
# Server runs on http://localhost:8000
```

### 5. Frontend Setup (in new terminal)

```bash
cd frontend
npm install
npm run dev
# Frontend runs on http://localhost:5173
```

## First Run Checklist

- [ ] Backend is running on port 8000
- [ ] Frontend is running on port 5173
- [ ] Database file created (`backend/trading_console.db`)
- [ ] Paper mode is enabled in `config.yaml` (for safety)
- [ ] Binance API credentials set in `.env` (or use testnet)

## Testing

1. Open http://localhost:5173
2. Navigate to Dashboard
3. You should see funding opportunities (if API is configured)
4. Try clicking a symbol to see the trade panel

## Troubleshooting

**Backend won't start:**
- Check Python version: `python --version` (need 3.11+)
- Check dependencies: `pip list | grep fastapi`
- Check port 8000 is not in use

**Frontend won't start:**
- Check Node version: `node --version` (need 18+)
- Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`

**API errors:**
- Check `.env` file has correct Binance credentials
- Check `config.yaml` exists
- Check backend logs for errors

**Database errors:**
- Ensure `backend/` directory is writable
- Check SQLite file permissions
