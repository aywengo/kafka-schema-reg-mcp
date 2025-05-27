#!/bin/bash

# Multi-Registry Complete Cleanup Script
# Removes all Docker resources to ensure a clean start

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_color $BLUE "🧹 Multi-Registry Complete Cleanup"

# Stop all containers
print_color $YELLOW "Stopping containers..."
docker stop kafka-dev kafka-prod schema-registry-dev schema-registry-prod akhq-multi mcp-server-multi 2>/dev/null || true

# Remove all containers
print_color $YELLOW "Removing containers..."
docker rm kafka-dev kafka-prod schema-registry-dev schema-registry-prod akhq-multi mcp-server-multi 2>/dev/null || true

# Remove networks
print_color $YELLOW "Removing networks..."
docker network rm tests_kafka-multi-test 2>/dev/null || true

# Remove volumes (if any)
print_color $YELLOW "Removing volumes..."
docker volume prune -f &>/dev/null || true

# Remove unused images
print_color $YELLOW "Cleaning up unused images..."
docker image prune -f &>/dev/null || true

# Clean up orphaned containers and networks
print_color $YELLOW "Cleaning up orphaned resources..."
docker container prune -f &>/dev/null || true
docker network prune -f &>/dev/null || true

# Kill any processes using our ports
print_color $YELLOW "Checking for port conflicts..."
ports=(38080 38081 38082 39092 39093 39094 39095)
for port in "${ports[@]}"; do
    if lsof -ti:$port &>/dev/null; then
        print_color $YELLOW "Killing processes on port $port..."
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
    fi
done

print_color $GREEN "✅ Complete cleanup finished!"
print_color $BLUE "You can now run: ./start_multi_registry_environment.sh" 