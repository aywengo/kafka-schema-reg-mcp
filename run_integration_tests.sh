#!/bin/bash

set -e

echo "Running Kafka Schema Registry MCP Integration Tests"
echo "=================================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to cleanup
cleanup() {
    echo -e "\n${GREEN}Cleaning up...${NC}"
    docker-compose down -v > /dev/null 2>&1
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Start services (suppress output)
echo -e "\n${GREEN}Starting services...${NC}"
docker-compose up -d > /dev/null 2>&1

# Enhanced service readiness check
echo -e "\n${GREEN}Waiting for services to be healthy...${NC}"
MAX_WAIT=120
WAIT_COUNT=0

check_service() {
    local url=$1
    local name=$2
    curl -s "$url" > /dev/null 2>&1
}

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    # Check all required services
    if check_service "http://localhost:38000/" "MCP Server" && \
       check_service "http://localhost:38081/" "Schema Registry"; then
        echo -e "\n${GREEN}All services are ready!${NC}"
        break
    fi
    
    echo -n "."
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT + 2))
done

if [ $WAIT_COUNT -eq $MAX_WAIT ]; then
    echo -e "\n${RED}Services did not become ready in time${NC}"
    echo -e "\n${RED}Docker service status:${NC}"
    docker-compose ps
    echo -e "\n${RED}MCP Server logs:${NC}"
    docker-compose logs --tail=20 mcp-server
    echo -e "\n${RED}Schema Registry logs:${NC}"
    docker-compose logs --tail=10 schema-registry-mcp
    exit 1
fi

# Additional wait for services to be fully ready
echo -e "\n${GREEN}Services ready! Waiting for full initialization...${NC}"
sleep 10

# Create a temporary file to capture test results for parsing
TEMP_OUTPUT=$(mktemp)

# Run tests with real-time output AND capture results
echo -e "\n${BLUE}Running Tests:${NC}"
echo "========================================"

# Use tee to show output in real-time AND capture it
if pytest tests/test_integration.py -v --tb=short --color=yes 2>&1 | tee "$TEMP_OUTPUT"; then
    TEST_RESULT=0
else
    TEST_RESULT=$?
fi

echo "========================================"

# Parse test results from captured output
TEST_OUTPUT=$(cat "$TEMP_OUTPUT")
PASSED=$(echo "$TEST_OUTPUT" | grep -o "[0-9]\+ passed" | grep -o "[0-9]\+" | head -1 || echo "0")
FAILED=$(echo "$TEST_OUTPUT" | grep -o "[0-9]\+ failed" | grep -o "[0-9]\+" | head -1 || echo "0")
SKIPPED=$(echo "$TEST_OUTPUT" | grep -o "[0-9]\+ skipped" | grep -o "[0-9]\+" | head -1 || echo "0")
ERRORS=$(echo "$TEST_OUTPUT" | grep -o "[0-9]\+ error" | grep -o "[0-9]\+" | head -1 || echo "0")

# Ensure all variables are integers (not empty)
PASSED=${PASSED:-0}
FAILED=${FAILED:-0}
SKIPPED=${SKIPPED:-0}
ERRORS=${ERRORS:-0}

# Calculate totals
TOTAL_TESTS=$((PASSED + FAILED + SKIPPED + ERRORS))

# Clean up temp file
rm -f "$TEMP_OUTPUT"

# Print enhanced summary
echo -e "\n${BLUE}=================================================="
echo -e "                TEST SUMMARY"
echo -e "==================================================${NC}"

# Check if we actually have failures (more accurate than exit code)
if [ "$FAILED" -gt 0 ] || [ "$ERRORS" -gt 0 ]; then
    echo -e "${RED}❌ Some tests failed or had issues!${NC}"
    TEST_RESULT=1
elif [ "$TOTAL_TESTS" -eq 0 ]; then
    echo -e "${RED}❌ No tests were run!${NC}"
    TEST_RESULT=1
else
    echo -e "${GREEN}✅ All tests completed successfully!${NC}"
fi

echo -e "\n${YELLOW}📊 Test Results:${NC}"
echo -e "  ${GREEN}✅ Passed:  ${PASSED}${NC}"
echo -e "  ${RED}❌ Failed:  ${FAILED}${NC}"
echo -e "  ${YELLOW}⏸️  Skipped: ${SKIPPED}${NC}"
echo -e "  ${RED}💥 Errors:  ${ERRORS}${NC}"
echo -e "  ${BLUE}📈 Total:   ${TOTAL_TESTS}${NC}"

# Show additional diagnostics if tests failed
if [ $TEST_RESULT -ne 0 ]; then
    echo -e "\n${YELLOW}🔍 Diagnostic Information:${NC}"
    
    echo -e "\n${BLUE}Service Status:${NC}"
    docker-compose ps
    
    echo -e "\n${BLUE}MCP Server Health:${NC}"
    if curl -s http://localhost:38000/ | jq . 2>/dev/null; then
        echo -e "${GREEN}✅ MCP Server is responding${NC}"
    else
        echo -e "${RED}❌ MCP Server is not responding${NC}"
        echo -e "\n${RED}MCP Server logs (last 15 lines):${NC}"
        docker-compose logs --tail=15 mcp-server
    fi
    
    echo -e "\n${BLUE}Schema Registry Health:${NC}"
    if curl -s http://localhost:38081/ >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Schema Registry is responding${NC}"
    else
        echo -e "${RED}❌ Schema Registry is not responding${NC}"
        echo -e "\n${RED}Schema Registry logs (last 10 lines):${NC}"
        docker-compose logs --tail=10 schema-registry-mcp
    fi
fi

echo -e "\n${BLUE}=================================================="
echo -e "                  FINISHED"
echo -e "==================================================${NC}"

exit $TEST_RESULT 