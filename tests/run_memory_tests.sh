#!/bin/bash
# Memory Functionality Test Runner

set -e

echo "=========================================="
echo "Memory Functionality Test Suite"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if API is running
echo -e "${BLUE}Checking API status...${NC}"
if curl -s http://localhost:15800/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API is running${NC}"
    API_RUNNING=true
else
    echo -e "${YELLOW}⚠️  API is not running${NC}"
    echo "Starting API in background..."
    cd /root/blue-psychology-test
    python app/main.py > /tmp/memory_test_api.log 2>&1 &
    API_PID=$!
    echo "API PID: $API_PID"
    
    # Wait for API to start
    echo "Waiting for API to start..."
    for i in {1..30}; do
        if curl -s http://localhost:15800/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ API started successfully${NC}"
            API_RUNNING=true
            break
        fi
        sleep 1
        echo -n "."
    done
    echo ""
    
    if [ "$API_RUNNING" != "true" ]; then
        echo -e "${RED}❌ Failed to start API${NC}"
        exit 1
    fi
fi

echo ""
echo "=========================================="
echo "Running Unit Tests"
echo "=========================================="
python test_memory_service_unit.py
UNIT_TEST_RESULT=$?

echo ""
echo "=========================================="
echo "Running Integration Tests"
echo "=========================================="
python test_memory_comprehensive.py
INTEGRATION_TEST_RESULT=$?

echo ""
echo "=========================================="
echo "Running Pytest Tests"
echo "=========================================="
pytest tests/test_memory_router.py -v --tb=short
PYTEST_RESULT=$?

echo ""
echo "=========================================="
echo "Test Results Summary"
echo "=========================================="

if [ $UNIT_TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ Unit Tests: PASSED${NC}"
else
    echo -e "${RED}❌ Unit Tests: FAILED${NC}"
fi

if [ $INTEGRATION_TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ Integration Tests: PASSED${NC}"
else
    echo -e "${RED}❌ Integration Tests: FAILED${NC}"
fi

if [ $PYTEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ Pytest Tests: PASSED${NC}"
else
    echo -e "${RED}❌ Pytest Tests: FAILED${NC}"
fi

echo ""

# Cleanup
if [ ! -z "$API_PID" ]; then
    echo "Stopping test API (PID: $API_PID)..."
    kill $API_PID 2>/dev/null || true
fi

# Exit with error if any test failed
if [ $UNIT_TEST_RESULT -ne 0 ] || [ $INTEGRATION_TEST_RESULT -ne 0 ] || [ $PYTEST_RESULT -ne 0 ]; then
    echo -e "${RED}Some tests failed${NC}"
    exit 1
else
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
fi
