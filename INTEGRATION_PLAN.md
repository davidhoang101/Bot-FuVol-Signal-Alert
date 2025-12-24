# Integration Plan - Binance Trading Console Web App

## Overview

This document outlines the step-by-step plan for integrating the web application into the existing codebase.

## Project Structure Created

```
futu_vol_alert/
├── backend/                    # NEW: FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── api/                # API routes
│   │   │   └── routes/        # Individual route modules
│   │   ├── core/              # Core config & logging
│   │   ├── db/                # Database models & session
│   │   ├── exchange/          # Binance exchange adapter (ccxt)
│   │   └── services/         # Business logic services
│   └── requirements.txt       # Python dependencies
│
├── frontend/                   # NEW: React frontend
│   ├── src/
│   │   ├── pages/             # Page components
│   │   ├── components/        # Reusable components
│   │   └── api/               # API client
│   ├── package.json           # Node dependencies
│   └── vite.config.ts         # Vite configuration
│
├── config.yaml                 # NEW: Non-secret config
├── .env                        # Secrets (create from .env.example)
├── WEB_APP_README.md          # Full documentation
└── SETUP_GUIDE.md             # Quick setup guide
```

## Files Created

### Backend (FastAPI)

1. **Core Application**
   - `backend/app/main.py` - FastAPI app with CORS, routes, error handling
   - `backend/app/core/config.py` - Configuration management
   - `backend/app/core/logging.py` - Logging setup

2. **Database**
   - `backend/app/db/models.py` - SQLAlchemy models (Trade, Order, EventLog)
   - `backend/app/db/session.py` - Database session management

3. **Exchange Adapter**
   - `backend/app/exchange/binance_ccxt.py` - Binance adapter using ccxt
     - Spot and futures clients
     - Retry logic with exponential backoff
     - Rate limiting

4. **Services**
   - `backend/app/services/funding_scanner.py` - Funding rate scanning
   - `backend/app/services/trade_executor.py` - Trade execution (delta-neutral)
   - `backend/app/services/monitoring.py` - Order/position monitoring

5. **API Routes**
   - `backend/app/api/routes/health.py` - Health check
   - `backend/app/api/routes/config.py` - Configuration endpoints
   - `backend/app/api/routes/markets.py` - Market data endpoints
   - `backend/app/api/routes/trade.py` - Trading endpoints
   - `backend/app/api/routes/orders.py` - Orders endpoints
   - `backend/app/api/routes/positions.py` - Positions endpoints
   - `backend/app/api/routes/balances.py` - Balances endpoints
   - `backend/app/api/routes/margin.py` - Margin endpoints
   - `backend/app/api/routes/emergency.py` - Emergency endpoints
   - `backend/app/api/routes/logs.py` - Logs endpoints

### Frontend (React)

1. **Pages**
   - `frontend/src/pages/Dashboard.tsx` - Funding scanner table
   - `frontend/src/pages/Symbol.tsx` - Symbol detail & trade panel
   - `frontend/src/pages/Monitor.tsx` - Orders/positions/logs monitoring
   - `frontend/src/pages/Settings.tsx` - Configuration view

2. **Components**
   - `frontend/src/components/Layout.tsx` - Main layout with navigation
   - `frontend/src/components/FundingTable.tsx` - Funding opportunities table
   - `frontend/src/components/TradeForm.tsx` - Trade execution form
   - `frontend/src/components/OrdersTable.tsx` - Orders table
   - `frontend/src/components/PositionsCard.tsx` - Positions display
   - `frontend/src/components/MarginCard.tsx` - Margin information
   - `frontend/src/components/LogsPanel.tsx` - Event logs display

3. **API Client**
   - `frontend/src/api/client.ts` - API client with all endpoints

### Configuration

- `config.yaml` - Non-secret configuration
- `.env.example` - Environment variables template
- `backend/requirements.txt` - Python dependencies
- `frontend/package.json` - Node dependencies

## Key Features Implemented

### 1. Funding Rate Scanner
- Scans all USDT perpetual contracts
- Filters by min funding rate, max spread, volume
- Sorts by funding rate (descending)
- Real-time refresh capability

### 2. Delta-Neutral Trading
- 2-phase execution: BUY spot → SHORT perp
- Automatic rollback if perp order fails
- Pre-trade validation (spread, margin, notional)
- Idempotency support via client_request_id

### 3. Monitoring
- Real-time order tracking (polling every 3s)
- Position monitoring with P&L
- Balance tracking (spot + futures)
- Margin ratio monitoring
- Event log streaming

### 4. Safety Features
- Paper mode (dry-run)
- Pre-trade validations
- Emergency close endpoint
- Margin checks

## Commands to Run

### Initial Setup

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### Running

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
python -m app.main

# Terminal 2: Frontend
cd frontend
npm run dev
```

## Integration with Existing Code

The web app is **separate** from the existing `main.py` volume alert system:

- **Existing**: `main.py` - Volume alert bot (runs independently)
- **New**: `backend/app/main.py` - Web API server (runs independently)

They can run simultaneously or separately. The web app uses:
- Same Binance API credentials (from `.env`)
- Same configuration pattern (`.env` + `config.yaml`)
- Different database (`trading_console.db` vs existing)

## Next Steps

1. **Test Backend**:
   - Start backend server
   - Test API endpoints via `/docs`
   - Verify database creation

2. **Test Frontend**:
   - Start frontend dev server
   - Navigate to Dashboard
   - Test funding scanner

3. **Test Trading** (in paper mode):
   - Select a symbol
   - Try opening delta-neutral position
   - Verify orders are created (simulated)

4. **Production Deployment**:
   - Set `paper_mode: false` when ready
   - Configure proper CORS origins
   - Set up reverse proxy (nginx)
   - Use PostgreSQL instead of SQLite

## Notes

- Paper mode is **enabled by default** in `config.yaml`
- All trades are simulated until `paper_mode: false`
- Database is SQLite (easy to migrate to PostgreSQL later)
- Frontend polls for updates (websockets can be added later)
- No authentication yet (add if needed for production)
