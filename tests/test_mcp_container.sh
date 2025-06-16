#!/bin/bash
# Test script for MCP container integration

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Docker Compose command detection
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "Error: Neither 'docker-compose' nor 'docker compose' command found"
    exit 1
fi

echo -e "${BLUE}Starting MCP Container Integration Test${NC}"
echo "========================================"

# Check if MCP server is running
if ! docker ps | grep -q "mcp-server"; then
    echo -e "${YELLOW}MCP server container not found. Starting test environment...${NC}"
    cd "$(dirname "$0")"
    $DOCKER_COMPOSE up -d --build mcp-server
    
    # Wait for container to be healthy
    echo -e "${BLUE}Waiting for MCP server to be healthy...${NC}"
    for i in {1..30}; do
        if docker inspect --format='{{.State.Health.Status}}' mcp-server 2>/dev/null | grep -q "healthy"; then
            echo -e "${GREEN}✓ MCP server is healthy${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
fi

# Test basic MCP communication
echo -e "\n${BLUE}Testing MCP protocol communication...${NC}"

# Test 1: List tools
echo -e "${BLUE}Test 1: Listing MCP tools${NC}"
RESPONSE=$(echo '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}' | \
    docker exec -i mcp-server python kafka_schema_registry_unified_mcp.py 2>/dev/null | \
    grep -E '"result"|"error"' | head -1)

if echo "$RESPONSE" | grep -q '"result"'; then
    echo -e "${GREEN}✓ Successfully listed MCP tools${NC}"
else
    echo -e "${RED}✗ Failed to list MCP tools${NC}"
    echo "Response: $RESPONSE"
    exit 1
fi

# Test 2: Call a simple tool
echo -e "\n${BLUE}Test 2: Calling list_subjects tool${NC}"
RESPONSE=$(echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"list_subjects","arguments":{}},"id":2}' | \
    docker exec -i mcp-server python kafka_schema_registry_unified_mcp.py 2>/dev/null | \
    grep -E '"result"|"error"' | head -1)

if echo "$RESPONSE" | grep -q '"result"'; then
    echo -e "${GREEN}✓ Successfully called list_subjects tool${NC}"
else
    echo -e "${RED}✗ Failed to call list_subjects tool${NC}"
    echo "Response: $RESPONSE"
    exit 1
fi

# Test 3: Multi-registry support
echo -e "\n${BLUE}Test 3: Testing multi-registry support${NC}"
RESPONSE=$(echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"list_subjects","arguments":{"registry_name":"dev"}},"id":3}' | \
    docker exec -i mcp-server python kafka_schema_registry_unified_mcp.py 2>/dev/null | \
    grep -E '"result"|"error"' | head -1)

if echo "$RESPONSE" | grep -q '"result"'; then
    echo -e "${GREEN}✓ Multi-registry mode is working${NC}"
else
    echo -e "${RED}✗ Multi-registry mode failed${NC}"
    echo "Response: $RESPONSE"
fi

echo -e "\n${GREEN}MCP Container Integration Test Complete!${NC}"
echo "========================================"

# Run full Python test suite if requested
if [[ "$1" == "--full" ]]; then
    echo -e "\n${BLUE}Running full Python test suite...${NC}"
    python3 test_mcp_container_integration.py -v
fi 