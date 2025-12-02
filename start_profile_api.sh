#!/bin/bash

cd /root/blue-psychology-test
source .venv/bin/activate

# Kill existing API
lsof -ti:15801 | xargs kill -9 2>/dev/null
sleep 1

# Start API in background
echo "Starting Profile Extractor API on port 15801..."
PYTHONPATH=/root/blue-psychology-test nohup uvicorn app.main:app --host 0.0.0.0 --port 15801 --reload > logs/profile_api.log 2>&1 &
API_PID=$!

echo "API started (PID: $API_PID)"
echo "Waiting for API to be ready..."
sleep 5

# Test API
echo ""
echo "=== Testing API ==="
curl -s http://localhost:15801/health | python3 -m json.tool

echo ""
echo ""
echo "API is running on http://localhost:15801"
echo "Logs: tail -f logs/profile_api.log"
echo "To stop: kill $API_PID"
echo "PID saved to: /tmp/profile_api.pid"
echo $API_PID > /tmp/profile_api.pid
