#!/bin/bash

# Blue Psychology - Full FastAPI Server Startup
# This starts ALL services (TTS, Image, Profile) on port 15800

cd /root/blue-psychology-test

echo "=========================================="
echo "🚀 Blue Psychology Full API Server"
echo "=========================================="
echo ""

# Kill any existing process on port 15800
echo "🔍 Checking for existing processes on port 15800..."
lsof -ti:15800 | xargs kill -9 2>/dev/null
sleep 1

# Create logs directory
mkdir -p logs

# Start the API
echo "🚀 Starting Full API Server..."
echo ""
nohup /root/blue-psychology-test/.venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 15800 --reload > logs/full_api.log 2>&1 &
API_PID=$!

# Save PID
echo $API_PID > /tmp/blue_full_api.pid

# Wait for startup
echo "⏳ Waiting for API to start..."
sleep 3

# Check if running
if ps -p $API_PID > /dev/null 2>&1; then
    echo ""
    echo "✅ API Started Successfully!"
    echo ""
    echo "📋 Details:"
    echo "   PID: $API_PID"
    echo "   Port: 15800"
    echo ""
    echo "🌐 Access Points:"
    echo "   Base URL:  http://localhost:15800"
    echo "   Docs:      http://localhost:15800/docs"
    echo "   Health:    http://localhost:15800/health"
    echo ""
    echo "📡 Available Services:"
    echo "   ✓ TTS (Text-to-Speech)    → /tts/*"
    echo "   ✓ Image Generation        → /image/*"
    echo "   ✓ Profile Extraction      → /profile/*"
    echo ""
    echo "📝 Management:"
    echo "   View logs:  tail -f logs/full_api.log"
    echo "   Stop API:   kill $API_PID"
    echo "   Or use:     ./stop_api.sh"
    echo ""
    echo "=========================================="
else
    echo ""
    echo "❌ Failed to start API"
    echo "Check logs: cat logs/full_api.log"
    exit 1
fi
