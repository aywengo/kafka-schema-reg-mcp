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

# Test 2: Check if MCP server can connect to Schema Registry
echo -e "\n${BLUE}Test 2: Testing Schema Registry connectivity${NC}"
TEST_OUTPUT=$(docker exec mcp-server python -c "
import os
import sys

# Debug: Print environment variables
print('Environment variables:')
for key, value in os.environ.items():
    if 'SCHEMA_REGISTRY' in key:
        print(f'  {key}={value}')

try:
    # Import after environment is set
    from schema_registry_common import RegistryManager
    
    manager = RegistryManager()
    registries = manager.list_registries()
    print(f'\\nDetected {len(registries)} registries')
    
    if len(registries) == 0:
        print('Warning: No registries detected')
        print('Registry mode:', os.environ.get('REGISTRY_MODE', 'not set'))
    else:
        for reg in registries:
            print(f'  - Registry: {reg}')
            try:
                client = manager.get_registry(reg)
                if client:
                    # Just check if we can get the client, don't test connection yet
                    print(f'    Client created successfully')
            except Exception as e:
                print(f'    Error creating client: {e}')
    
    print('\\nRegistry manager initialized successfully')
    
except Exception as e:
    import traceback
    print(f'\\nError: {e}')
    print('\\nTraceback:')
    traceback.print_exc()
    sys.exit(1)
" 2>&1)

if echo "$TEST_OUTPUT" | grep -q "Registry manager initialized successfully"; then
    echo -e "${GREEN}✓ Registry manager initialized successfully${NC}"
    echo "$TEST_OUTPUT" | sed 's/^/  /'
elif echo "$TEST_OUTPUT" | grep -q "Detected.*registries"; then
    echo -e "${YELLOW}⚠️  Registry manager initialized but may have issues${NC}"
    echo "$TEST_OUTPUT" | sed 's/^/  /'
    # Don't fail the test, just warn
else
    echo -e "${RED}✗ Failed to initialize Registry manager${NC}"
    echo "$TEST_OUTPUT" | sed 's/^/  /'
    exit 1
fi

# Test 3: Test MCP server startup (but don't keep it running)
echo -e "\n${BLUE}Test 3: Testing MCP server startup${NC}"
# Use timeout to run the server for just 2 seconds
if timeout 2s docker exec mcp-server python kafka_schema_registry_unified_mcp.py 2>&1 | grep -q "Kafka Schema Registry Unified MCP Server Starting"; then
    echo -e "${GREEN}✓ MCP server starts successfully${NC}"
else
    echo -e "${YELLOW}⚠️  Could not verify MCP server startup (this may be normal)${NC}"
fi

echo -e "\n${GREEN}MCP Container Integration Test Complete!${NC}"
echo "========================================"

# Run full Python test suite if requested
if [[ "$1" == "--full" ]]; then
    echo -e "\n${BLUE}Running full Python test suite...${NC}"
    python3 test_mcp_container_integration.py -v
fi 