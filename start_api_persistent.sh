#!/bin/bash

# Start API in detached screen session
SESSION_NAME="blue-api"

# Kill existing session if exists
screen -S $SESSION_NAME -X quit 2>/dev/null

# Start new session
echo "Starting API in screen session: $SESSION_NAME"
screen -dmS $SESSION_NAME bash -c "cd /root/blue-psychology-test && /root/blue-psychology-test/.venv/bin/python3 run_api.py"

sleep 2

echo ""
echo "✅ API started in background!"
echo ""
echo "Commands:"
echo "  View logs:    screen -r $SESSION_NAME"
echo "  Detach:       Ctrl+A then D"
echo "  Stop:         screen -S $SESSION_NAME -X quit"
echo "  List:         screen -ls"
echo ""
echo "API running on: http://localhost:15800"
echo "Docs: http://localhost:15800/docs"
