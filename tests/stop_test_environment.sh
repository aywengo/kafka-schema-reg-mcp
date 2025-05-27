#!/bin/bash

# Stop Test Environment Script
# 
# This script stops the Docker-based Kafka and Schema Registry test environment
# and cleans up resources.

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

print_header "STOPPING TEST ENVIRONMENT"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    print_color $RED "❌ Docker is not installed or not in PATH"
    exit 1
fi

# Check if services are running
if ! docker ps | grep -q "schema-registry-test\|kafka-test"; then
    print_color $YELLOW "⚠️  No test services are currently running"
    exit 0
fi

print_color $BLUE "🛑 Stopping test services..."

# Stop and remove containers
docker-compose -f "$SCRIPT_DIR/docker-compose.test.yml" down

print_color $GREEN "✅ Test services stopped"

# Optional: Remove volumes (uncomment if you want to clean up data)
# print_color $BLUE "🧹 Cleaning up volumes..."
# docker-compose -f "$SCRIPT_DIR/docker-compose.test.yml" down -v
# print_color $GREEN "✅ Volumes cleaned up"

# Check if containers are really stopped
if docker ps | grep -q "schema-registry-test\|kafka-test"; then
    print_color $YELLOW "⚠️  Some containers may still be running"
    print_color $BLUE "Force stopping remaining containers..."
    docker stop kafka-test schema-registry-test 2>/dev/null || true
    docker rm kafka-test schema-registry-test 2>/dev/null || true
fi

print_color $GREEN "🎉 Test environment has been stopped"
print_color $WHITE "To start the environment again:"
print_color $WHITE "  ./start_test_environment.sh" 