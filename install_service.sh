#!/bin/bash

echo "Installing Blue Psychology API as system service..."

# Copy service file
sudo cp blue-api.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable blue-api.service

# Start service
sudo systemctl start blue-api.service

echo ""
echo "✅ Service installed successfully!"
echo ""
echo "Commands:"
echo "  Start:   sudo systemctl start blue-api"
echo "  Stop:    sudo systemctl stop blue-api"
echo "  Restart: sudo systemctl restart blue-api"
echo "  Status:  sudo systemctl status blue-api"
echo "  Logs:    sudo journalctl -u blue-api -f"
