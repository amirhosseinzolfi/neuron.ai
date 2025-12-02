#!/bin/bash
# Netdata Service Management Script

show_usage() {
    echo "=== Netdata Management ==="
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  status       - Show netdata service status"
    echo "  stop         - Stop netdata service"
    echo "  start        - Start netdata service"
    echo "  restart      - Restart netdata service"
    echo "  disable      - Disable netdata from starting at boot"
    echo "  enable       - Enable netdata to start at boot"
    echo "  full-disable - Stop netdata and disable autostart"
    echo "  full-enable  - Start netdata and enable autostart"
    echo "  resources    - Show netdata resource usage"
    echo ""
}

show_status() {
    echo "=== Netdata Service Status ==="
    systemctl status netdata --no-pager -l
    echo ""
    echo "Boot status: $(systemctl is-enabled netdata 2>&1)"
}

show_resources() {
    echo "=== Netdata Resource Usage ==="
    if pgrep -x "netdata" > /dev/null; then
        ps aux | grep "[n]etdata" | awk '{printf "PID: %-6s CPU: %5s%% MEM: %5s%% RSS: %8s KB CMD: %s\n", $2, $3, $4, $6, substr($0, index($0,$11))}'
        echo ""
        total_mem=$(pgrep -x "netdata" | xargs ps -o rss= -p 2>/dev/null | awk '{sum+=$1} END {print sum/1024}')
        echo "Total Memory: ${total_mem:-0} MB"
    else
        echo "Netdata is not running"
    fi
}

case "$1" in
    status)
        show_status
        ;;
    stop)
        echo "Stopping netdata..."
        sudo systemctl stop netdata
        echo "✓ Netdata stopped"
        show_status
        ;;
    start)
        echo "Starting netdata..."
        sudo systemctl start netdata
        echo "✓ Netdata started"
        show_status
        ;;
    restart)
        echo "Restarting netdata..."
        sudo systemctl restart netdata
        echo "✓ Netdata restarted"
        show_status
        ;;
    disable)
        echo "Disabling netdata from autostart..."
        sudo systemctl disable netdata
        echo "✓ Netdata autostart disabled"
        echo "Boot status: $(systemctl is-enabled netdata 2>&1)"
        ;;
    enable)
        echo "Enabling netdata autostart..."
        sudo systemctl enable netdata
        echo "✓ Netdata autostart enabled"
        echo "Boot status: $(systemctl is-enabled netdata 2>&1)"
        ;;
    full-disable)
        echo "Stopping netdata and disabling autostart..."
        sudo systemctl stop netdata
        sudo systemctl disable netdata
        echo "✓ Netdata fully disabled"
        show_status
        ;;
    full-enable)
        echo "Starting netdata and enabling autostart..."
        sudo systemctl enable netdata
        sudo systemctl start netdata
        echo "✓ Netdata fully enabled"
        show_status
        ;;
    resources)
        show_resources
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
