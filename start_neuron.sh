#!/usr/bin/env bash
set -euo pipefail

cd /root/neuron
mkdir -p /root/neuron/logs

export PYTHONUNBUFFERED=1
export PATH="/root/neuron/.venv/bin:$PATH"

# Load environment variables if present
if [ -f /root/neuron/.env ]; then
  set -a
  . /root/neuron/.env
  set +a
fi

# Kill any existing bot instances to prevent Telegram Conflict errors
echo "Stopping any existing bot instances..."
pkill -f "python.*telegrambot.py" 2>/dev/null || true
sleep 2

echo "Starting Telegram bot..."
python /root/neuron/telegrambot.py >> /root/neuron/logs/neuron-telegram.log 2>&1 &
TELEGRAM_PID=$!

echo "Starting API server on port 15808..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 15808

# When uvicorn exits, kill the bot too
kill $TELEGRAM_PID 2>/dev/null || true
