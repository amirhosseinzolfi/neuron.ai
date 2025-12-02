#!/bin/bash

# Stop Blue Psychology API

PID_FILE="/tmp/blue_full_api.pid"

if [ -f $PID_FILE ]; then
    PID=$(cat $PID_FILE)
    echo "🛑 Stopping API (PID: $PID)..."
    kill $PID 2>/dev/null
    rm -f $PID_FILE
    echo "✅ API stopped"
else
    echo "⚠️  No PID file found, killing by port..."
    lsof -ti:15800 | xargs kill -9 2>/dev/null
    echo "✅ Processes on port 15800 killed"
fi
