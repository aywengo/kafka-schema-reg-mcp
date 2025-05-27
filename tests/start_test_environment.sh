#!/bin/bash

# Start Test Environment Script
# 
# This script starts the Docker-based Kafka and Schema Registry test environment
# from within the tests directory for running integration tests.

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
    print_color $CYAN "$(printf '=%.0s' {1..70})"
    print_color $WHITE "  $title"
    print_color $CYAN "$(printf '=%.0s' {1..70})"
    echo
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_header "KAFKA SCHEMA REGISTRY TEST ENVIRONMENT SETUP"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    print_color $RED "❌ Docker is not installed or not in PATH"
    print_color $YELLOW "Please install Docker Desktop: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

if ! docker info &> /dev/null; then
    print_color $RED "❌ Docker is not running"
    print_color $YELLOW "Please start Docker Desktop and try again"
    exit 1
fi

print_color $GREEN "✅ Docker is available and running"

# Clean up any existing containers (including stopped ones)
print_color $BLUE "🧹 Cleaning up any existing containers..."
docker stop kafka-test schema-registry-test 2>/dev/null || true
docker rm kafka-test schema-registry-test 2>/dev/null || true
docker-compose -f "$SCRIPT_DIR/docker-compose.test.yml" down --remove-orphans 2>/dev/null || true
sleep 2

# Start the test environment
print_color $BLUE "🚀 Starting Kafka and Schema Registry test environment..."
docker-compose -f "$SCRIPT_DIR/docker-compose.test.yml" up -d

# Wait for services to be ready
print_color $BLUE "⏳ Waiting for services to start..."
sleep 10

# Check Kafka health
print_color $BLUE "🔍 Checking Kafka health..."
timeout=60
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker exec kafka-test kafka-topics --bootstrap-server localhost:9092 --list &> /dev/null; then
        print_color $GREEN "✅ Kafka is ready"
        break
    fi
    sleep 5
    elapsed=$((elapsed + 5))
    print_color $YELLOW "   Waiting for Kafka... ($elapsed/$timeout seconds)"
done

if [ $elapsed -ge $timeout ]; then
    print_color $RED "❌ Kafka failed to start within $timeout seconds"
    print_color $YELLOW "Check logs with: docker logs kafka-test"
    exit 1
fi

# Check Schema Registry health
print_color $BLUE "🔍 Checking Schema Registry health..."
print_color $YELLOW "   Note: Schema Registry may take up to 2 minutes to initialize..."
timeout=120
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if curl -s http://localhost:8081/subjects &> /dev/null; then
        print_color $GREEN "✅ Schema Registry is ready on http://localhost:8081"
        break
    fi
    sleep 10
    elapsed=$((elapsed + 10))
    print_color $YELLOW "   Waiting for Schema Registry... ($elapsed/$timeout seconds)"
    
    # Show helpful info every 30 seconds
    if [ $((elapsed % 30)) -eq 0 ] && [ $elapsed -gt 0 ]; then
        print_color $BLUE "   💡 If this takes too long, check logs with: docker logs schema-registry-test"
    fi
done

if [ $elapsed -ge $timeout ]; then
    print_color $RED "❌ Schema Registry failed to start within $timeout seconds"
    print_color $YELLOW "Showing last 10 lines of Schema Registry logs:"
    docker logs --tail 10 schema-registry-test 2>&1 | sed 's/^/   /'
    print_color $YELLOW ""
    print_color $YELLOW "Troubleshooting steps:"
    print_color $YELLOW "1. Check full logs: docker logs schema-registry-test"
    print_color $YELLOW "2. Check Kafka logs: docker logs kafka-test"
    print_color $YELLOW "3. Try restarting: ./stop_test_environment.sh && ./start_test_environment.sh"
    exit 1
fi

# Final verification
print_color $BLUE "🔍 Final verification..."
response=$(curl -s http://localhost:8081/subjects)
if [ "$response" = "[]" ]; then
    print_color $GREEN "✅ Schema Registry is responding correctly"
else
    print_color $YELLOW "⚠️  Schema Registry responded but with unexpected content: $response"
fi

print_header "TEST ENVIRONMENT READY"

print_color $GREEN "🎉 Test environment is ready!"
print_color $WHITE "Services running:"
print_color $WHITE "  • Kafka: localhost:9092"
print_color $WHITE "  • Schema Registry: localhost:8081"
echo
print_color $BLUE "To run tests:"
print_color $WHITE "  ./run_comprehensive_tests.sh"
echo
print_color $BLUE "To stop the environment:"
print_color $WHITE "  ./stop_test_environment.sh"
print_color $WHITE "  # OR"
print_color $WHITE "  docker-compose -f docker-compose.test.yml down"
echo
print_color $BLUE "To check service status:"
print_color $WHITE "  docker ps | grep -E 'kafka-test|schema-registry-test'"
echo
print_color $BLUE "To view logs:"
print_color $WHITE "  docker logs kafka-test"
print_color $WHITE "  docker logs schema-registry-test" 