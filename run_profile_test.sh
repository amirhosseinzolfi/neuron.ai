#!/bin/bash

cd /root/blue-psychology-test
source .venv/bin/activate

# Kill any existing API
pkill -f "uvicorn app.main:app"
sleep 2

# Start API
PYTHONPATH=/root/blue-psychology-test uvicorn app.main:app --host 0.0.0.0 --port 15801 --reload &
API_PID=$!
echo "Starting API (PID: $API_PID)..."
sleep 5

# Test
echo -e "\n=== Testing Profile Extractor ===\n"

echo "Test 1: Create profile from scratch"
curl -s -X POST http://localhost:15801/profile/extract-json \
  -H "Content-Type: application/json" \
  -d '{"messages": ["My name is Alex Johnson", "I am 29 years old", "I work as a UX designer"]}' | python3 -m json.tool

echo -e "\n\nAPI running on http://localhost:15801"
echo "API PID: $API_PID"
echo "To stop: kill $API_PID"
