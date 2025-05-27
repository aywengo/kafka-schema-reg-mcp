#!/bin/bash

# Stop Multi-Registry Test Environment Script
# 
# This script stops the multi-registry test environment and cleans up resources

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to print section headers
print_header() {
    local title=$1
    echo
    print_color $CYAN "$(printf '=%.0s' {1..50})"
    print_color $WHITE "  $title"
    print_color $CYAN "$(printf '=%.0s' {1..50})"
    echo
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_header "STOPPING MULTI-REGISTRY ENVIRONMENT"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    print_color $RED "❌ Docker is not installed or not in PATH"
    exit 1
fi

# Check if services are running
multi_containers=(kafka-dev kafka-prod schema-registry-dev schema-registry-prod akhq-multi mcp-server-multi)
running_containers=()

for container in "${multi_containers[@]}"; do
    if docker ps | grep -q "$container"; then
        running_containers+=("$container")
    fi
done

if [ ${#running_containers[@]} -eq 0 ]; then
    print_color $YELLOW "⚠️  No multi-registry services are currently running"
    exit 0
fi

print_color $BLUE "🛑 Stopping multi-registry services..."
print_color $YELLOW "   Found running: ${running_containers[*]}"

# Stop using docker-compose
docker-compose -f "$SCRIPT_DIR/docker-compose.multi-test.yml" down

print_color $GREEN "✅ Multi-registry services stopped"

# Force stop and remove any remaining containers
print_color $BLUE "🧹 Cleaning up remaining containers..."
for container in "${multi_containers[@]}"; do
    docker stop "$container" 2>/dev/null || true
    docker rm "$container" 2>/dev/null || true
done

# Clean up networks
print_color $BLUE "🌐 Cleaning up networks..."
docker network rm tests_kafka-multi-test 2>/dev/null || true

print_color $GREEN "🎉 Multi-registry environment has been stopped and cleaned up"
print_color $WHITE "To start the environment again:"
print_color $WHITE "  ./start_multi_registry_environment.sh" 