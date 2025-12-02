#!/bin/bash

# Blue Psychology Test API - Startup Script
# This script checks dependencies and starts the FastAPI server

echo "=================================================="
echo "🧠 Blue Psychology Test API Server"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Python is installed
echo -e "${BLUE}Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✅ Python ${PYTHON_VERSION} found${NC}"
echo ""

# Check if pip is installed
echo -e "${BLUE}Checking pip installation...${NC}"
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}❌ pip is not installed${NC}"
    echo "Please install pip"
    exit 1
fi
echo -e "${GREEN}✅ pip is installed${NC}"
echo ""

# Check if FastAPI is installed
echo -e "${BLUE}Checking FastAPI installation...${NC}"
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  FastAPI not found${NC}"
    echo -e "${BLUE}Installing dependencies...${NC}"
    pip3 install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Dependencies installed successfully${NC}"
    else
        echo -e "${RED}❌ Failed to install dependencies${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ FastAPI is installed${NC}"
fi
echo ""

# Check if database is initialized
echo -e "${BLUE}Checking database...${NC}"
if [ ! -f "database/bot.db" ]; then
    echo -e "${YELLOW}⚠️  Database not found, initializing...${NC}"
    python3 -c "import db; db.init_db()"
    echo -e "${GREEN}✅ Database initialized${NC}"
else
    echo -e "${GREEN}✅ Database found${NC}"
fi
echo ""

# Ask for port
echo -e "${BLUE}Which port would you like to use?${NC}"
read -p "Port [default: 8000]: " PORT
PORT=${PORT:-8000}
echo ""

# Start server
echo "=================================================="
echo -e "${GREEN}🚀 Starting API Server on port ${PORT}${NC}"
echo "=================================================="
echo ""
echo -e "${YELLOW}Access points:${NC}"
echo -e "  📍 API Base:          http://localhost:${PORT}"
echo -e "  📚 Documentation:     http://localhost:${PORT}/docs"
echo -e "  🔄 Alternative Docs:  http://localhost:${PORT}/redoc"
echo -e "  ❤️  Health Check:      http://localhost:${PORT}/health"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo "=================================================="
echo ""

# Change to api directory
cd "$(dirname "$0")/.."

# Start the server
python3 api.py
