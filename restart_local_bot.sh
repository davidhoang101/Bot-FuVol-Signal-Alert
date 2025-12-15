#!/bin/bash
# Script to restart local bot after Railway is stopped

echo "🔄 Restarting local bot..."

# Kill existing local bot if running
LOCAL_PID=$(ps aux | grep "python.*main.py" | grep -v grep | awk '{print $2}')
if [ ! -z "$LOCAL_PID" ]; then
    echo "   Stopping existing bot (PID: $LOCAL_PID)..."
    kill $LOCAL_PID
    sleep 2
fi

# Wait a bit for Railway to release polling (if stopped)
echo "   Waiting for polling to be available..."
sleep 5

# Start bot
echo "   Starting bot..."
python main.py

