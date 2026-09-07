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

echo "Starting Telegram bot..."
nohup python /root/neuron/telegrambot.py >> /root/neuron/logs/neuron-telegram.log 2>&1 &

echo "Starting API server..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 15808
