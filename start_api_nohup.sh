#!/bin/bash

cd /root/blue-psychology-test

# Kill existing process
lsof -ti:15800 | xargs kill -9 2>/dev/null
sleep 1

# Start API with nohup
echo "Starting Blue Psychology API..."
nohup /root/blue-psychology-test/.venv/bin/python3 run_api.py > logs/api.log 2>&1 &
API_PID=$!

echo $API_PID > /tmp/blue_api.pid

sleep 3

echo ""
echo "✅ API started successfully!"
echo "   PID: $API_PID"
echo "   Port: 15800"
echo ""
echo "Access:"
echo "  API:  http://localhost:15800"
echo "  Docs: http://localhost:15800/docs"
echo ""
echo "Commands:"
echo "  Logs:  tail -f logs/api.log"
echo "  Stop:  kill $API_PID"
