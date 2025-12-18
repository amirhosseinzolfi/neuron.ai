#!/bin/bash

echo "🔄 Restarting Blue Psychology Bot..."

# Kill existing bot process
echo "⏹️  Stopping existing bot..."
pkill -f telegrambot.py
sleep 2

# Verify it's stopped
if pgrep -f telegrambot.py > /dev/null; then
    echo "⚠️  Force killing bot..."
    pkill -9 -f telegrambot.py
    sleep 1
fi

# Start bot in background
echo "🚀 Starting bot..."
cd /root/blue-psychology-test
nohup python3 telegrambot.py > bot.log 2>&1 &

sleep 3

# Check if bot started
if pgrep -f telegrambot.py > /dev/null; then
    echo "✅ Bot restarted successfully!"
    echo "📋 View logs: tail -f /root/blue-psychology-test/bot.log"
else
    echo "❌ Failed to start bot. Check logs."
    exit 1
fi
