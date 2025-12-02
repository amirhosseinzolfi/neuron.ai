# VSCode Remote SSH Optimization Guide

This guide helps prevent VSCode Remote SSH disconnections during heavy processing.

## Problem
VSCode Remote SSH disconnects during:
- Heavy file processing
- Large git operations
- Running tests or builds
- High CPU/memory usage
- File watcher overload

## Solution Components

### 1. Server-Side Optimization (Run on SSH Server)

```bash
# Run the optimization script
./server_ssh_optimization.sh
```

This script:
- Optimizes SSH daemon keep-alive settings
- Increases system file watchers
- Cleans VSCode server cache
- Creates resource monitoring tool

### 2. Client-Side SSH Configuration (Your Local Machine)

Add to `~/.ssh/config`:

```ssh
Host your-server
    HostName your.server.ip
    User your-username
    
    # Keep connection alive
    ServerAliveInterval 30
    ServerAliveCountMax 6
    TCPKeepAlive yes
    
    # Reuse connections (faster reconnection)
    ControlMaster auto
    ControlPath ~/.ssh/sockets/%r@%h-%p
    ControlPersist 600
    
    # Performance
    Compression yes
    IPQoS throughput
    ConnectTimeout 60
```

Create sockets directory:
```bash
mkdir -p ~/.ssh/sockets
chmod 700 ~/.ssh/sockets
```

### 3. VSCode Settings (Already configured in .vscode/settings.json)

Key optimizations:
- Extended connection timeouts
- SSH keep-alive enabled
- Reduced file watchers (excludes venv, logs, cache)
- Limited Python analysis memory
- Auto-save enabled
- Disabled auto-fetch/refresh for git

### 4. VSCode Extensions Optimization

Install these extensions for better performance:
- Remote - SSH (ms-vscode-remote.remote-ssh)
- Remote - SSH: Editing Configuration Files

Disable heavy extensions when working remotely:
- GitLens (enable only when needed)
- Heavy linters (use CLI instead)
- Auto-formatters on save (use manual formatting)

### 5. Network Optimization

**For unstable connections:**

Add to your local VSCode `settings.json`:
```json
{
  "remote.SSH.useLocalServer": true,
  "remote.SSH.remoteServerListenOnSocket": true,
  "remote.SSH.enableDynamicForwarding": false
}
```

**For stable but slow connections:**
```json
{
  "remote.SSH.useLocalServer": false,
  "remote.SSH.enableAgentForwarding": false
}
```

### 6. Project-Specific Optimizations

**Exclude large directories from file watching:**

In `.vscode/settings.json`:
```json
{
  "files.watcherExclude": {
    "**/node_modules/**": true,
    "**/venv/**": true,
    "**/__pycache__/**": true,
    "**/build/**": true,
    "**/dist/**": true,
    "**/.git/objects/**": true,
    "**/logs/**": true,
    "**/*.log": true
  }
}
```

### 7. Troubleshooting Commands

**Check connection status:**
```bash
~/monitor_vscode.sh
```

**Check SSH connection on client:**
```bash
ssh -v your-server  # verbose mode to see connection details
```

**Kill stale VSCode processes:**
```bash
pkill -f "vscode-server"
```

**Clear VSCode server completely:**
```bash
rm -rf ~/.vscode-server
# Then reconnect - VSCode will reinstall
```

**Check server resources:**
```bash
# CPU and Memory
htop

# Disk I/O
iotop

# Network
netstat -an | grep :22
```

### 8. Advanced: Use tmux/screen for Long Operations

For very long-running operations, use terminal multiplexers:

```bash
# Install tmux
sudo apt-get install tmux

# Start tmux session
tmux new -s mywork

# Run your heavy process
python your_heavy_script.py

# Detach: Press Ctrl+b then d
# Reattach later: tmux attach -t mywork
```

### 9. Performance Tuning for Python Projects

Add to your workspace settings:

```json
{
  "python.analysis.memory.keepLibraryAst": false,
  "python.analysis.maxMemory": 4096,
  "python.analysis.indexing": false,
  "python.languageServer": "Pylance",
  "python.analysis.diagnosticMode": "openFilesOnly"
}
```

### 10. Quick Fixes Checklist

**If disconnections persist:**

- [ ] Check internet connection stability
- [ ] Verify SSH server is not overloaded (CPU/RAM)
- [ ] Ensure adequate disk space on server
- [ ] Check firewall/router settings (NAT timeout)
- [ ] Update VSCode and Remote-SSH extension
- [ ] Restart SSH service on server
- [ ] Clear VSCode server cache
- [ ] Reduce number of open files in VSCode
- [ ] Close unused terminals
- [ ] Disable resource-intensive extensions

**Network-specific issues:**

- [ ] If behind NAT: Set router NAT timeout to max (3600s)
- [ ] If using VPN: Enable VPN keep-alive
- [ ] If using WiFi: Switch to wired connection
- [ ] If using mobile hotspot: Check carrier restrictions

### 11. Monitoring Script Usage

```bash
# Run monitoring script
~/monitor_vscode.sh

# Schedule periodic checks (optional)
crontab -e
# Add: */15 * * * * ~/monitor_vscode.sh >> ~/vscode_monitor.log
```

### 12. Emergency Reconnection

If connection drops during work:

1. Don't panic - auto-save should have saved your work
2. Wait 30 seconds before reconnecting
3. VSCode will attempt to restore your workspace state
4. Check `~/monitor_vscode.sh` for resource issues
5. If needed, kill stale processes and reconnect

## Best Practices

1. **Commit frequently** - Don't lose work to disconnections
2. **Use auto-save** - Already enabled in settings
3. **Close unused files** - Reduces memory usage
4. **Split heavy operations** - Break into smaller chunks
5. **Use CLI for heavy tasks** - Run builds/tests in SSH terminal
6. **Monitor resources** - Use monitoring script regularly
7. **Keep server updated** - Regular system updates
8. **Clean regularly** - Remove old logs, caches

## Testing Your Configuration

```bash
# Test 1: Connection stability (run on local machine)
while true; do
  ssh your-server "echo 'OK: $(date)'"
  sleep 30
done

# Test 2: Server resources
ssh your-server "~/monitor_vscode.sh"

# Test 3: File operations
ssh your-server "time find ~/blue-psychology-test -type f | wc -l"
```

## Additional Resources

- VSCode Remote SSH: https://code.visualstudio.com/docs/remote/ssh
- SSH Config: https://man.openbsd.org/ssh_config
- Troubleshooting: https://code.visualstudio.com/docs/remote/troubleshooting

## Support

If issues persist after following this guide:
1. Check VSCode Remote SSH logs: View → Output → Remote-SSH
2. Check SSH logs on server: `sudo journalctl -u sshd -f`
3. Check system logs: `dmesg | tail -50`
