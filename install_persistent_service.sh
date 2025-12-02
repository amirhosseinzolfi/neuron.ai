#!/bin/bash

echo "=========================================="
echo "📦 Installing Blue Psychology API Service"
echo "=========================================="
echo ""

# Create logs directory
mkdir -p /root/blue-psychology-test/logs

# Copy service file
echo "📋 Copying service file..."
sudo cp blue-psychology-api.service /etc/systemd/system/

# Reload systemd
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

# Enable service
echo "✅ Enabling service to start on boot..."
sudo systemctl enable blue-psychology-api.service

# Start service
echo "🚀 Starting service..."
sudo systemctl start blue-psychology-api.service

# Wait a moment
sleep 3

# Check status
echo ""
echo "=========================================="
echo "📊 Service Status:"
echo "=========================================="
sudo systemctl status blue-psychology-api.service --no-pager

echo ""
echo "=========================================="
echo "✅ Installation Complete!"
echo "=========================================="
echo ""
echo "🎯 Your API is now running on port 15800"
echo ""
echo "🌐 Access Points:"
echo "   http://localhost:15800"
echo "   http://localhost:15800/docs"
echo ""
echo "📡 Available Services:"
echo "   • TTS:     POST /tts/generate"
echo "   • Image:   POST /image/generate"
echo "   • Profile: POST /profile/extract"
echo ""
echo "🔧 Management Commands:"
echo "   Start:   sudo systemctl start blue-psychology-api"
echo "   Stop:    sudo systemctl stop blue-psychology-api"
echo "   Restart: sudo systemctl restart blue-psychology-api"
echo "   Status:  sudo systemctl status blue-psychology-api"
echo "   Logs:    sudo journalctl -u blue-psychology-api -f"
echo ""
echo "🔥 The API will auto-start on system boot!"
echo "=========================================="
