#!/bin/bash

# Stop Unified Test Environment Script
# 
# This script stops the unified Docker-based multi-registry test environment.

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Docker Compose command detection
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "Error: Neither 'docker-compose' nor 'docker compose' command found"
    exit 1
fi

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_color $CYAN "🛑 Stopping Unified Test Environment"
print_color $CYAN "====================================="
echo

# Parse command line arguments for cleanup level
CLEANUP_LEVEL="${1:-normal}"

case "$CLEANUP_LEVEL" in
    "soft")
        print_color $BLUE "🔄 Soft stop: Stopping containers only"
        ;;
    "hard"|"clean")
        print_color $BLUE "🧹 Hard stop: Stopping containers, removing volumes and networks"
        ;;
    *)
        print_color $BLUE "🛑 Normal stop: Stopping and removing containers"
        ;;
esac

cd "$SCRIPT_DIR"

# Stop and remove containers using docker-compose
print_color $BLUE "Stopping containers..."
if [ -f "docker-compose.yml" ]; then
    if [ "$CLEANUP_LEVEL" = "soft" ]; then
        $DOCKER_COMPOSE stop
    else
        $DOCKER_COMPOSE down --remove-orphans
    fi
else
    print_color $YELLOW "⚠️  docker-compose.yml not found, stopping containers manually..."
fi

# Additional manual cleanup for any remaining containers
print_color $BLUE "Cleaning up any remaining containers..."
docker stop kafka-dev kafka-prod schema-registry-dev schema-registry-prod akhq-ui 2>/dev/null || true
docker rm kafka-dev kafka-prod schema-registry-dev schema-registry-prod akhq-ui 2>/dev/null || true

# Legacy container cleanup (from old setup)
docker stop kafka-test schema-registry-test akhq-multi mcp-server-multi 2>/dev/null || true
docker rm kafka-test schema-registry-test akhq-multi mcp-server-multi 2>/dev/null || true

if [ "$CLEANUP_LEVEL" = "hard" ] || [ "$CLEANUP_LEVEL" = "clean" ]; then
    print_color $BLUE "Performing deep cleanup..."
    
    # Remove networks
    print_color $BLUE "Removing networks..."
    docker network rm kafka-test-network 2>/dev/null || true
    docker network rm tests_kafka-multi-test 2>/dev/null || true
    docker network rm tests_kafka-network-test 2>/dev/null || true
    
    # Remove named volumes
    print_color $BLUE "Removing named volumes..."
    docker volume rm kafka-dev-data kafka-prod-data 2>/dev/null || true
    
    # Prune unused volumes
    print_color $BLUE "Pruning unused volumes..."
    docker volume prune -f &>/dev/null || true
    
    # Prune unused networks
    print_color $BLUE "Pruning unused networks..."
    docker network prune -f &>/dev/null || true
fi

# Verify cleanup
print_color $BLUE "🔍 Verifying cleanup..."

# Check if any containers are still running
running_containers=$(docker ps --format "table {{.Names}}" | grep -E "(kafka|schema-registry|akhq)" || true)
if [ -n "$running_containers" ]; then
    print_color $YELLOW "⚠️  Some containers are still running:"
    echo "$running_containers" | sed 's/^/   /'
else
    print_color $GREEN "✅ All test containers stopped"
fi

# Check port availability
print_color $BLUE "Checking port availability..."
ports=(9092 9094 38080 38081 38082 39092 39093 39095)
ports_in_use=()

for port in "${ports[@]}"; do
    if lsof -i :$port &> /dev/null; then
        ports_in_use+=($port)
    fi
done

if [ ${#ports_in_use[@]} -eq 0 ]; then
    print_color $GREEN "✅ All test ports are now available"
else
    print_color $YELLOW "⚠️  Some ports are still in use: ${ports_in_use[*]}"
    print_color $YELLOW "   You may need to wait a moment for them to be released"
fi

echo
print_color $GREEN "🎉 Test environment cleanup completed!"
print_color $WHITE ""
print_color $BLUE "📋 Next steps:"
print_color $WHITE "  • Start environment:     ./start_test_environment.sh"
print_color $WHITE "  • Start DEV only:        ./start_test_environment.sh dev"
print_color $WHITE "  • Start with UI:         ./start_test_environment.sh ui"
print_color $WHITE ""
print_color $BLUE "🔄 Stop options:"
print_color $WHITE "  • Soft stop:             ./stop_test_environment.sh soft"
print_color $WHITE "  • Normal stop:           ./stop_test_environment.sh"
print_color $WHITE "  • Hard cleanup:          ./stop_test_environment.sh clean" 