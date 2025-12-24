# Binance Trading Console - Web Application

A full-stack web application for scanning Binance funding rates and executing delta-neutral trading strategies with a clean, operator-driven interface.

## Features

- **Funding Rate Scanner**: Real-time scanning of Binance perpetual futures with filtering and sorting
- **Delta-Neutral Trading**: Safe 2-phase execution (BUY spot + SHORT perp) with automatic rollback on failure
- **Order & Position Monitoring**: Real-time tracking of orders, positions, balances, and margin
- **Paper Mode**: Dry-run mode for testing without real trades
- **Safety Features**: Pre-trade validations, emergency close, and margin checks

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, ccxt
- **Frontend**: React 18, TypeScript, Vite, TailwindCSS
- **Database**: SQLite (for persistence)
- **Exchange**: Binance via ccxt

## Project Structure

```
.
├── backend/
│   └── app/
│       ├── main.py              # FastAPI app entry point
│       ├── api/                  # API routes
│       ├── core/                 # Config, logging
│       ├── db/                   # Database models & session
│       ├── exchange/             # Binance exchange adapter
│       └── services/             # Business logic services
├── frontend/
│   └── src/
│       ├── pages/                # Page components
│       ├── components/           # Reusable components
│       └── api/                  # API client
├── config.yaml                   # Non-secret configuration
└── .env                          # Secrets (create from .env.example)
```

## Setup Instructions

### Prerequisites

- Python 3.11+
- Node.js 18+
- Binance API credentials (optional for paper mode)

### Backend Setup

1. **Create virtual environment**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cd ..
   cp .env.example .env
   # Edit .env with your Binance API credentials
   ```

4. **Configure settings**:
   - Edit `config.yaml` to adjust trading parameters
   - Set `paper_mode: true` for dry-run (recommended for testing)

5. **Initialize database**:
   ```bash
   cd backend
   python -c "from app.db.session import init_db; import asyncio; asyncio.run(init_db())"
   ```

6. **Run backend server**:
   ```bash
   python -m app.main
   # Or: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   The API will be available at `http://localhost:8000`
   API docs at `http://localhost:8000/docs`

### Frontend Setup

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Run development server**:
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:5173`

### Production Build

**Backend**:
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Frontend**:
```bash
cd frontend
npm run build
# Serve the dist/ directory with a web server (nginx, etc.)
```

## Configuration

### Environment Variables (.env)

- `BINANCE_API_KEY`: Your Binance API key
- `BINANCE_API_SECRET`: Your Binance API secret
- `BINANCE_ENABLE_TESTNET`: Set to `true` for testnet (recommended for testing)
- `DEBUG`: Enable debug mode
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)

### Config File (config.yaml)

- `funding_scanner`: Scanner settings (min_rate, max_spread_bps, refresh_sec)
- `trading`: Trading limits and safety parameters
- `paper_mode`: Enable/disable dry-run mode

## Usage

### 1. Scan Funding Opportunities

1. Navigate to Dashboard
2. Set filters (min funding rate, max spread)
3. View opportunities sorted by funding rate
4. Click a symbol to open the trade panel

### 2. Execute Delta-Neutral Trade

1. Select a symbol from the scanner
2. Enter notional amount (USDT)
3. Set leverage (default: 1x)
4. Click "Open Delta-Neutral"
   - Phase 1: BUY spot
   - Phase 2: SHORT perp (with automatic rollback if fails)

### 3. Monitor Positions

1. Navigate to Monitor page
2. View:
   - Open orders (spot + perp)
   - Current positions
   - Account balances
   - Margin information
   - Event logs

### 4. Close Position

1. In Symbol page or Monitor page
2. Click "Close Delta-Neutral"
   - Closes perp position
   - Sells spot balance

## Safety Features

- **Paper Mode**: All orders are simulated (no real trades)
- **Pre-trade Validation**: Checks spread, margin, and notional limits
- **Automatic Rollback**: If perp order fails, spot position is automatically reverted
- **Emergency Close**: Emergency endpoint to close all positions for a symbol
- **Margin Monitoring**: Real-time margin ratio and free margin tracking

## API Endpoints

### Health & Config
- `GET /api/health` - Health check
- `GET /api/config` - Get configuration
- `POST /api/config/reload` - Reload configuration

### Markets
- `GET /api/markets/funding` - Get funding opportunities
- `GET /api/markets/symbol/{symbol}/snapshot` - Get symbol snapshot

### Trading
- `POST /api/trade/open_delta_neutral` - Open delta-neutral position
- `POST /api/trade/close_delta_neutral` - Close delta-neutral position
- `POST /api/trade/place_order` - Place manual order

### Monitoring
- `GET /api/orders` - Get orders
- `GET /api/positions` - Get positions
- `GET /api/balances` - Get balances
- `GET /api/margin` - Get margin info
- `GET /api/logs/tail` - Get event logs

### Emergency
- `POST /api/emergency/close_all` - Emergency close all positions

## Important Notes

1. **Paper Mode**: Always test in paper mode first. Set `paper_mode: true` in `config.yaml`
2. **Binance Futures**: Ensure your API key has futures trading permissions
3. **Rate Limits**: The app includes rate limiting, but be mindful of Binance API limits
4. **Idempotency**: Use `client_request_id` to prevent duplicate trades
5. **Delta Drift**: Monitor delta drift (spot_qty + perp_qty should be ~0)

## Troubleshooting

### Backend Issues

- **Database errors**: Ensure SQLite file is writable
- **Binance connection**: Check API credentials and network
- **Import errors**: Ensure all dependencies are installed

### Frontend Issues

- **API connection**: Ensure backend is running on port 8000
- **CORS errors**: Check CORS settings in `backend/app/main.py`
- **Build errors**: Clear `node_modules` and reinstall

## Development

### Running Tests

```bash
# Backend tests (when implemented)
cd backend
pytest

# Frontend tests (when implemented)
cd frontend
npm test
```

### Code Structure

- **Backend**: Follow FastAPI best practices, use async/await
- **Frontend**: React functional components with hooks
- **Database**: SQLAlchemy ORM with SQLite
- **Exchange**: ccxt adapter with retry logic

## License

[Your License Here]

## Disclaimer

This software is for educational purposes. Trading cryptocurrencies involves risk. Always test in paper mode first and never trade more than you can afford to lose.
