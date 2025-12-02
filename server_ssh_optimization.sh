#!/bin/bash
# Server-side SSH optimization script
# Run this on your SSH server to optimize SSH daemon settings

echo "=== SSH Server Optimization ==="

# Backup existing sshd_config
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)

# Check and update SSH server settings
echo "Checking SSH daemon configuration..."

# Function to update or add SSH config
update_ssh_config() {
    local key=$1
    local value=$2
    local config_file="/etc/ssh/sshd_config"
    
    if sudo grep -q "^#\?${key}" "$config_file"; then
        sudo sed -i "s/^#\?${key}.*/${key} ${value}/" "$config_file"
        echo "Updated: ${key} ${value}"
    else
        echo "${key} ${value}" | sudo tee -a "$config_file" > /dev/null
        echo "Added: ${key} ${value}"
    fi
}

# Optimize SSH daemon settings
update_ssh_config "ClientAliveInterval" "30"
update_ssh_config "ClientAliveCountMax" "6"
update_ssh_config "TCPKeepAlive" "yes"
update_ssh_config "Compression" "yes"

# Increase MaxSessions for multiplexing
update_ssh_config "MaxSessions" "10"
update_ssh_config "MaxStartups" "10:30:60"

echo ""
echo "Testing SSH configuration..."
if sudo sshd -t; then
    echo "✓ SSH configuration is valid"
    echo ""
    echo "Restarting SSH service..."
    sudo systemctl restart sshd || sudo systemctl restart ssh
    echo "✓ SSH service restarted"
else
    echo "✗ SSH configuration has errors. Restoring backup..."
    sudo cp /etc/ssh/sshd_config.backup.$(date +%Y%m%d)* /etc/ssh/sshd_config
    echo "Backup restored. Please check the configuration manually."
    exit 1
fi

echo ""
echo "=== System Resource Optimization ==="

# Increase file watchers limit
echo "Current fs.inotify.max_user_watches: $(cat /proc/sys/fs/inotify/max_user_watches)"
echo "fs.inotify.max_user_watches=524288" | sudo tee -a /etc/sysctl.conf > /dev/null
sudo sysctl -p

# Increase file descriptors
echo "Current fs.file-max: $(cat /proc/sys/fs/file-max)"
echo "fs.file-max=2097152" | sudo tee -a /etc/sysctl.conf > /dev/null
sudo sysctl -p

echo ""
echo "=== VSCode Server Optimization ==="

# Clean old VSCode server instances
echo "Cleaning old VSCode server processes..."
pkill -f "vscode-server" || echo "No stale VSCode processes found"

# Clean VSCode server cache
VSCODE_SERVER_DIR="$HOME/.vscode-server"
if [ -d "$VSCODE_SERVER_DIR" ]; then
    echo "Cleaning VSCode server cache..."
    rm -rf "$VSCODE_SERVER_DIR/.cache" 2>/dev/null
    rm -rf "$VSCODE_SERVER_DIR/data/logs/old" 2>/dev/null
    echo "✓ Cache cleaned"
fi

echo ""
echo "=== Resource Monitoring Setup ==="

# Create a monitoring script
cat > ~/monitor_vscode.sh << 'MONITOR_EOF'
#!/bin/bash
# Monitor VSCode server resources

echo "=== VSCode Server Resource Usage ==="
echo "Time: $(date)"
echo ""

if pgrep -f "vscode-server" > /dev/null; then
    echo "Active VSCode Processes:"
    ps aux | grep "[v]scode-server" | awk '{printf "PID: %s | CPU: %s%% | MEM: %s%% | CMD: %s\n", $2, $3, $4, substr($0, index($0,$11))}'
    echo ""
    
    # Memory usage
    total_mem=$(pgrep -f "vscode-server" | xargs ps -o rss= -p | awk '{sum+=$1} END {print sum/1024}')
    echo "Total VSCode Memory Usage: ${total_mem} MB"
    
    # Connection count
    conn_count=$(ss -tn | grep -c ":22 ")
    echo "Active SSH Connections: ${conn_count}"
else
    echo "No VSCode server processes running"
fi

echo ""
echo "System Resources:"
free -h
echo ""
echo "Load Average:"
uptime
MONITOR_EOF

chmod +x ~/monitor_vscode.sh

echo ""
echo "=== Optimization Complete ==="
echo ""
echo "✓ SSH daemon optimized"
echo "✓ System resources optimized"
echo "✓ VSCode server cache cleaned"
echo "✓ Monitoring script created: ~/monitor_vscode.sh"
echo ""
echo "Next steps:"
echo "1. Configure your local SSH client (see ssh_config_optimization.txt)"
echo "2. Update VSCode settings (see .vscode/settings.json)"
echo "3. Run ~/monitor_vscode.sh to check resource usage"
echo ""
echo "Note: You may need to reconnect your SSH session for changes to take effect."
