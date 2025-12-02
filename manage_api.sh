#!/bin/bash

# Blue Psychology API Management Script

PORT=15800
PID_FILE="/tmp/blue_api.pid"
LOG_FILE="logs/api.log"

case "$1" in
    start)
        if [ -f $PID_FILE ]; then
            PID=$(cat $PID_FILE)
            if ps -p $PID > /dev/null 2>&1; then
                echo "❌ API already running (PID: $PID)"
                exit 1
            fi
        fi
        
        echo "🚀 Starting Blue Psychology API..."
        cd /root/blue-psychology-test
        mkdir -p logs
        nohup /root/blue-psychology-test/.venv/bin/python3 run_api.py > $LOG_FILE 2>&1 &
        echo $! > $PID_FILE
        sleep 2
        
        if ps -p $(cat $PID_FILE) > /dev/null 2>&1; then
            echo "✅ API started successfully!"
            echo "   PID: $(cat $PID_FILE)"
            echo "   URL: http://localhost:$PORT"
            echo "   Docs: http://localhost:$PORT/docs"
        else
            echo "❌ Failed to start API"
            exit 1
        fi
        ;;
        
    stop)
        if [ ! -f $PID_FILE ]; then
            echo "❌ API not running"
            exit 1
        fi
        
        PID=$(cat $PID_FILE)
        echo "🛑 Stopping API (PID: $PID)..."
        kill $PID 2>/dev/null
        rm -f $PID_FILE
        echo "✅ API stopped"
        ;;
        
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
        
    status)
        if [ -f $PID_FILE ]; then
            PID=$(cat $PID_FILE)
            if ps -p $PID > /dev/null 2>&1; then
                echo "✅ API is running (PID: $PID)"
                echo "   URL: http://localhost:$PORT"
                exit 0
            else
                echo "❌ API not running (stale PID file)"
                rm -f $PID_FILE
                exit 1
            fi
        else
            echo "❌ API not running"
            exit 1
        fi
        ;;
        
    logs)
        tail -f $LOG_FILE
        ;;
        
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
