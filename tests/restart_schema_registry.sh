#!/bin/bash

# Restart Schema Registry Only
# Use this when Kafka is working but Schema Registry has issues

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_header() {
    local title=$1
    echo
    print_color $CYAN "$(printf '=%.0s' {1..50})"
    print_color $WHITE "  $title"
    print_color $CYAN "$(printf '=%.0s' {1..50})"
    echo
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_header "RESTARTING SCHEMA REGISTRY"

# Check if Kafka is running
if ! docker ps | grep -q kafka-test; then
    print_color $RED "❌ Kafka container is not running"
    print_color $YELLOW "Please start the full environment: ./start_test_environment.sh"
    exit 1
fi

print_color $GREEN "✅ Kafka is running"

# Stop and remove Schema Registry container
print_color $BLUE "🛑 Stopping Schema Registry container..."
docker stop schema-registry-test 2>/dev/null || true
docker rm schema-registry-test 2>/dev/null || true

# Wait a bit
sleep 2

# Start just the Schema Registry
print_color $BLUE "🚀 Starting Schema Registry..."
docker-compose -f "$SCRIPT_DIR/docker-compose.test.yml" up -d schema-registry-test

# Wait for it to start
print_color $BLUE "⏳ Waiting for Schema Registry to start..."
sleep 15

# Check health with extended timeout
print_color $BLUE "🔍 Checking Schema Registry health..."
timeout=90
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if curl -s http://localhost:8081/subjects &> /dev/null; then
        print_color $GREEN "✅ Schema Registry is ready on http://localhost:8081"
        
        # Test the response
        response=$(curl -s http://localhost:8081/subjects)
        print_color $BLUE "Response: $response"
        
        print_color $GREEN "🎉 Schema Registry restart successful!"
        print_color $WHITE "You can now run: ./run_comprehensive_tests.sh"
        exit 0
    fi
    
    sleep 5
    elapsed=$((elapsed + 5))
    print_color $YELLOW "   Waiting... ($elapsed/$timeout seconds)"
    
    # Show logs every 30 seconds
    if [ $((elapsed % 30)) -eq 0 ] && [ $elapsed -gt 0 ]; then
        print_color $BLUE "Last 5 lines of Schema Registry logs:"
        docker logs --tail 5 schema-registry-test 2>/dev/null | sed 's/^/   /' || true
    fi
done

print_color $RED "❌ Schema Registry failed to start within $timeout seconds"
print_color $YELLOW "Showing recent logs:"
docker logs --tail 15 schema-registry-test 2>&1 | sed 's/^/   /'
print_color $YELLOW ""
print_color $YELLOW "Try the simplified configuration:"
print_color $WHITE "   ./stop_test_environment.sh"
print_color $WHITE "   docker-compose -f docker-compose.simple.yml up -d"
exit 1 