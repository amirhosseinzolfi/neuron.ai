#!/bin/bash

# Blue Psychology Test Bot - Environment Setup Script
# This script helps you set up your .env file with new API keys

echo "🔐 Blue Psychology Test Bot - Security Fix Setup"
echo "=================================================="
echo ""
echo "⚠️  Your API keys were LEAKED and disabled by Google!"
echo "📝 This script will help you create a new .env file"
echo ""

# Check if .env already exists
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Setup cancelled. Please edit .env manually."
        exit 1
    fi
fi

echo ""
echo "📋 You need to provide the following API keys:"
echo "   1. Google Gemini API Keys (get from: https://makersuite.google.com/app/apikey)"
echo "   2. Telegram Bot Token (get from: @BotFather)"
echo ""
echo "💡 Tip: You can use the SAME Gemini API key for all services"
echo ""

# Function to read API key
read_key() {
    local prompt="$1"
    local var_name="$2"
    local key=""
    
    while [ -z "$key" ]; do
        read -p "$prompt: " key
        if [ -z "$key" ]; then
            echo "❌ Key cannot be empty!"
        fi
    done
    
    echo "$key"
}

# Read primary key
echo "🔑 Enter your Google Gemini API Key:"
PRIMARY_KEY=$(read_key "Primary API Key" "GOOGLE_API_KEY_PRIMARY")

echo ""
read -p "Use the same key for all services? (Y/n): " -n 1 -r
echo
USE_SAME_KEY=true
if [[ $REPLY =~ ^[Nn]$ ]]; then
    USE_SAME_KEY=false
fi

# Set all keys
if [ "$USE_SAME_KEY" = true ]; then
    SECONDARY_KEY="$PRIMARY_KEY"
    ANALYZE_KEY="$PRIMARY_KEY"
    IMAGE_KEY="$PRIMARY_KEY"
    HISTORY_KEY="$PRIMARY_KEY"
    NEURON_KEY="$PRIMARY_KEY"
    USER_INFO_KEY="$PRIMARY_KEY"
    MCP_KEY="$PRIMARY_KEY"
    echo "✅ Using same key for all services"
else
    echo ""
    echo "🔑 Enter additional API keys (or press Enter to use primary key):"
    SECONDARY_KEY=$(read -p "Secondary Key [Enter=use primary]: " key && echo "${key:-$PRIMARY_KEY}")
    ANALYZE_KEY=$(read -p "Analyze Key [Enter=use primary]: " key && echo "${key:-$PRIMARY_KEY}")
    IMAGE_KEY=$(read -p "Image Key [Enter=use primary]: " key && echo "${key:-$PRIMARY_KEY}")
    HISTORY_KEY=$(read -p "History Key [Enter=use primary]: " key && echo "${key:-$PRIMARY_KEY}")
    NEURON_KEY=$(read -p "Neuron Key [Enter=use primary]: " key && echo "${key:-$PRIMARY_KEY}")
    USER_INFO_KEY=$(read -p "User Info Key [Enter=use primary]: " key && echo "${key:-$PRIMARY_KEY}")
    MCP_KEY=$(read -p "MCP Key [Enter=use primary]: " key && echo "${key:-$PRIMARY_KEY}")
fi

echo ""
echo "🤖 Enter your Telegram Bot Token:"
BOT_TOKEN=$(read_key "Telegram Bot Token" "TELEGRAM_BOT_TOKEN")

# Create .env file
cat > .env << EOF
# Blue Psychology Test Bot - Environment Variables
# Generated on: $(date)

# ============================================
# GOOGLE GEMINI API KEYS
# ============================================
GOOGLE_API_KEY_PRIMARY=$PRIMARY_KEY
GOOGLE_API_KEY_SECONDARY=$SECONDARY_KEY
GOOGLE_API_KEY_ANALYZE=$ANALYZE_KEY
GOOGLE_API_KEY_IMAGE=$IMAGE_KEY
GOOGLE_API_KEY_HISTORY=$HISTORY_KEY
GOOGLE_API_KEY_NEURON=$NEURON_KEY
GOOGLE_API_KEY_USER_INFO=$USER_INFO_KEY
GOOGLE_API_KEY_MCP=$MCP_KEY

# ============================================
# TELEGRAM BOT
# ============================================
TELEGRAM_BOT_TOKEN=$BOT_TOKEN

# ============================================
# OPENAI COMPATIBLE API (G4F)
# ============================================
OPENAI_BASE_URL=http://localhost:15207/v1
OPENAI_MODEL=gemini-flash-latest

# ============================================
# AI HISTORY SETTINGS
# ============================================
AI_HISTORY_TRIM_THRESHOLD=15
AI_HISTORY_RETENTION=5
AI_HISTORY_SUMMARY_INTERVAL=5

# ============================================
# LOGGING
# ============================================
LOG_LEVEL=INFO
EOF

echo ""
echo "✅ .env file created successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Install dependencies: pip install -r requirements.txt"
echo "   2. Start the bot: python telegrambot.py"
echo ""
echo "🔒 Security reminder:"
echo "   - Never commit .env file to git"
echo "   - Keep your API keys secret"
echo "   - Rotate keys regularly"
echo ""
echo "✅ Setup complete!"
