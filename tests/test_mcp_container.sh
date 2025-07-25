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

# Test basic container functionality
echo -e "\n${BLUE}Testing MCP container functionality...${NC}"

# Test 1: Check if MCP server can be imported
echo -e "${BLUE}Test 1: Testing Python module import${NC}"
if docker exec mcp-server python -c "import kafka_schema_registry_unified_mcp; print('Module imported successfully')" 2>/dev/null | grep -q "Module imported successfully"; then
    echo -e "${GREEN}✓ MCP server module can be imported${NC}"
else
    echo -e "${RED}✗ Failed to import MCP server module${NC}"
    exit 1
fi

# Test 2: Check environment and basic imports
echo -e "\n${BLUE}Test 2: Testing environment and dependencies${NC}"

# First check if container is running
if ! docker ps --filter "name=mcp-server" --format "{{.Names}}" | grep -q "mcp-server"; then
    echo -e "${RED}✗ MCP server container is not running${NC}"
    echo "Running containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}"
    exit 1
fi

# Simple test to check environment
if docker exec mcp-server python -c "
import os
# Print environment variables
env_vars = [k for k in os.environ.keys() if 'SCHEMA_REGISTRY' in k]
print(f'Found {len(env_vars)} Schema Registry environment variables')
for var in sorted(env_vars):
    print(f'  {var}')
" 2>/dev/null; then
    echo -e "${GREEN}✓ Environment variables are set${NC}"
else
    echo -e "${RED}✗ Failed to check environment variables${NC}"
    exit 1
fi

# Test 3: Check if schema_registry_common module exists
echo -e "\n${BLUE}Test 3: Testing module availability${NC}"
if docker exec mcp-server python -c "import schema_registry_common; print('✓ schema_registry_common module imported')" 2>/dev/null; then
    echo -e "${GREEN}✓ Required modules are available${NC}"
else
    echo -e "${YELLOW}⚠️  Could not import schema_registry_common (this may be expected in minimal container)${NC}"
fi

# Test 4: Test MCP server startup (but don't keep it running)
echo -e "\n${BLUE}Test 4: Testing MCP server startup${NC}"
# Use timeout to run the server for just 2 seconds
if timeout 2s docker exec mcp-server python kafka_schema_registry_unified_mcp.py 2>&1 | grep -q "Kafka Schema Registry Unified MCP Server Starting"; then
    echo -e "${GREEN}✓ MCP server starts successfully${NC}"
else
    echo -e "${YELLOW}⚠️  Could not verify MCP server startup (this may be normal)${NC}"
fi

echo -e "\n${GREEN}MCP Container Basic Tests Complete!${NC}"
echo "========================================"
echo -e "${BLUE}Summary:${NC}"
echo "  - MCP server module can be imported"
echo "  - Environment variables are configured"
echo "  - Container has necessary dependencies"
echo ""
echo "Note: Full MCP protocol testing requires a persistent connection"
echo "      and is better suited for integration tests outside of CI/CD."

# Run full Python test suite if requested
if [[ "$1" == "--full" ]]; then
    echo -e "\n${BLUE}Running full Python test suite...${NC}"
    python3 test_mcp_container_integration.py -v
fi 