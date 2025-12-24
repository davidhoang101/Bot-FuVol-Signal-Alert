#!/bin/bash
# Script to run bot on localhost

echo "🚀 Starting Binance Futures Volume Alert Bot (Localhost)"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Running setup..."
    bash setup.sh
    echo ""
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "Creating .env from template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env file. Please edit it with your configuration!"
    else
        echo "❌ .env.example not found. Creating basic .env..."
        cat > .env << EOF
# Binance API (optional for public data)
BINANCE_API_KEY=
BINANCE_API_SECRET=
BINANCE_TESTNET=false

# Detection Parameters
MIN_VOLUME_THRESHOLD=1000000
SPIKE_RATIO_THRESHOLD=2.0
BASELINE_WINDOW_MINUTES=60
COOLDOWN_PERIOD_MINUTES=15
UPDATE_INTERVAL_SECONDS=5

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/volume_alert.log

# Telegram Bot (optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TELEGRAM_AUTO_TOP10_INTERVAL_MINUTES=0

# Funding Scanner
ENABLE_FUNDING_SCANNER=true
FUNDING_SCAN_INTERVAL_SECONDS=300
HIGH_FUNDING_RATE_THRESHOLD=0.001
LOW_FUNDING_RATE_THRESHOLD=-0.001
FUNDING_RATE_CHANGE_THRESHOLD=0.0005
FUNDING_ALERT_COOLDOWN_MINUTES=60
EOF
        echo "✅ Created basic .env file. Please edit it with your configuration!"
    fi
    echo ""
    echo "Press Enter to continue after editing .env (or Ctrl+C to exit)..."
    read
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Check if bot is already running
LOCAL_PID=$(ps aux | grep "python.*main.py" | grep -v grep | awk '{print $2}')
if [ ! -z "$LOCAL_PID" ]; then
    echo "⚠️  Bot is already running (PID: $LOCAL_PID)"
    echo "   Stopping existing bot..."
    kill $LOCAL_PID
    sleep 2
fi

# Start the bot
echo "✅ Starting bot..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
python main.py
