#!/bin/bash

# Unified Test Environment Startup Script
# 
# This script starts the unified Docker-based multi-registry Kafka and Schema Registry
# test environment that supports both single-registry and multi-registry testing.
#
# For single-registry tests: Use DEV registry on localhost:38081
# For multi-registry tests: Use both DEV (38081) and PROD (38082) registries

set -e  # Exit on any error

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

print_header "UNIFIED KAFKA SCHEMA REGISTRY TEST ENVIRONMENT"

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

# Parse command line arguments
FULL_STACK=false
SERVICES=""

case "${1:-}" in
    "dev"|"single")
        SERVICES="kafka-dev schema-registry-dev"
        print_color $BLUE "🎯 Starting single-registry mode (DEV only)"
        ;;
    "multi"|"full")
        FULL_STACK=true
        print_color $BLUE "🎯 Starting full multi-registry environment"
        ;;
    "ui")
        FULL_STACK=true
        print_color $BLUE "🎯 Starting full environment with UI"
        ;;
    *)
        print_color $BLUE "🎯 Starting full multi-registry environment (default)"
        FULL_STACK=true
        ;;
esac

# Check port availability
print_color $BLUE "🔍 Checking port availability..."
if [ "$FULL_STACK" = true ]; then
    ports=(38080 38081 38082 9092 9094 39092 39093 39095)
else
    ports=(38081 9092 9094)
fi

for port in "${ports[@]}"; do
    if lsof -i :$port &> /dev/null; then
        print_color $RED "❌ Port $port is in use"
        print_color $YELLOW "Please stop the service using this port and try again"
        exit 1
    fi
done
print_color $GREEN "✅ All required ports are available"

# Complete cleanup first
print_color $YELLOW "🧹 Performing complete cleanup..."
$DOCKER_COMPOSE -f "$SCRIPT_DIR/docker-compose.yml" down --remove-orphans 2>/dev/null || true
docker stop kafka-dev kafka-prod schema-registry-dev schema-registry-prod akhq-ui 2>/dev/null || true
docker rm kafka-dev kafka-prod schema-registry-dev schema-registry-prod akhq-ui 2>/dev/null || true
docker network rm kafka-test-network 2>/dev/null || true
docker volume prune -f &>/dev/null || true

print_color $BLUE "🚀 Starting test environment..."

cd "$SCRIPT_DIR"

# Start services based on mode
if [ "$FULL_STACK" = true ]; then
    print_color $WHITE "   Starting: 2 Kafka clusters, 2 Schema Registries, AKHQ UI"
    $DOCKER_COMPOSE up -d
else
    print_color $WHITE "   Starting: 1 Kafka cluster (DEV), 1 Schema Registry (DEV)"
    $DOCKER_COMPOSE up -d $SERVICES
fi

# Wait a moment for containers to initialize
sleep 15

# Wait for DEV services to be ready
print_color $BLUE "⏳ Waiting for DEV services to be ready..."

# Wait for Kafka DEV
print_color $BLUE "Checking Kafka DEV (localhost:9092)..."
timeout=90
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker exec kafka-dev kafka-topics --bootstrap-server localhost:9092 --list &> /dev/null; then
        print_color $GREEN "✅ Kafka DEV is ready"
        break
    fi
    sleep 5
    elapsed=$((elapsed + 5))
    print_color $YELLOW "   Waiting for Kafka DEV... ($elapsed/$timeout seconds)"
done

if [ $elapsed -ge $timeout ]; then
    print_color $RED "❌ Kafka DEV failed to start within $timeout seconds"
    print_color $YELLOW "Check logs with: docker logs kafka-dev"
    exit 1
fi

# Wait for Schema Registry DEV
print_color $BLUE "Checking Schema Registry DEV (localhost:38081)..."
timeout=120
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if curl -s http://localhost:38081/subjects &> /dev/null; then
        print_color $GREEN "✅ Schema Registry DEV is ready"
        break
    fi
    sleep 10
    elapsed=$((elapsed + 10))
    print_color $YELLOW "   Waiting for Schema Registry DEV... ($elapsed/$timeout seconds)"
    
    # Show helpful info every 30 seconds
    if [ $((elapsed % 30)) -eq 0 ] && [ $elapsed -gt 0 ]; then
        print_color $BLUE "   💡 If this takes too long, check logs with: docker logs schema-registry-dev"
    fi
done

if [ $elapsed -ge $timeout ]; then
    print_color $RED "❌ Schema Registry DEV failed to start within $timeout seconds"
    print_color $YELLOW "Showing last 10 lines of Schema Registry DEV logs:"
    docker logs --tail 10 schema-registry-dev 2>&1 | sed 's/^/   /'
    exit 1
fi

# Wait for PROD services if in full mode
if [ "$FULL_STACK" = true ]; then
    print_color $BLUE "⏳ Waiting for PROD services to be ready..."
    
    # Wait for Kafka PROD
    print_color $BLUE "Checking Kafka PROD (localhost:39093)..."
    timeout=90
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if docker exec kafka-prod kafka-topics --bootstrap-server localhost:9093 --list &> /dev/null; then
            print_color $GREEN "✅ Kafka PROD is ready"
            break
        fi
        sleep 5
        elapsed=$((elapsed + 5))
        print_color $YELLOW "   Waiting for Kafka PROD... ($elapsed/$timeout seconds)"
    done

    if [ $elapsed -ge $timeout ]; then
        print_color $RED "❌ Kafka PROD failed to start within $timeout seconds"
        print_color $YELLOW "Check logs with: docker logs kafka-prod"
        exit 1
    fi
    
    # Wait for Schema Registry PROD
    print_color $BLUE "Checking Schema Registry PROD (localhost:38082)..."
    timeout=120
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if curl -s http://localhost:38082/subjects &> /dev/null; then
            print_color $GREEN "✅ Schema Registry PROD is ready"
            break
        fi
        sleep 10
        elapsed=$((elapsed + 10))
        print_color $YELLOW "   Waiting for Schema Registry PROD... ($elapsed/$timeout seconds)"
    done

    if [ $elapsed -ge $timeout ]; then
        print_color $RED "❌ Schema Registry PROD failed to start within $timeout seconds"
        print_color $YELLOW "Showing last 10 lines of Schema Registry PROD logs:"
        docker logs --tail 10 schema-registry-prod 2>&1 | sed 's/^/   /'
        exit 1
    fi
    
    # Wait for AKHQ UI if it's running
    if docker ps --format "table {{.Names}}" | grep -q "akhq-ui"; then
        print_color $BLUE "Checking AKHQ UI (localhost:38080)..."
        timeout=120
        elapsed=0
        while [ $elapsed -lt $timeout ]; do
            if curl -s http://localhost:38080/api/health &> /dev/null; then
                print_color $GREEN "✅ AKHQ UI is ready"
                break
            fi
            sleep 10
            elapsed=$((elapsed + 10))
            print_color $YELLOW "   Waiting for AKHQ UI... ($elapsed/$timeout seconds)"
        done

        if [ $elapsed -ge $timeout ]; then
            print_color $YELLOW "⚠️  AKHQ UI did not start within $timeout seconds (non-critical)"
        fi
    fi
fi

# Final verification
print_color $BLUE "🔍 Final verification..."
dev_response=$(curl -s http://localhost:38081/subjects)
if [ "$dev_response" = "[]" ]; then
    print_color $GREEN "✅ Schema Registry DEV is responding correctly"
else
    print_color $YELLOW "⚠️  Schema Registry DEV responded but with unexpected content: $dev_response"
fi

if [ "$FULL_STACK" = true ]; then
    prod_response=$(curl -s http://localhost:38082/subjects)
    if [ "$prod_response" = "[]" ]; then
        print_color $GREEN "✅ Schema Registry PROD is responding correctly"
    else
        print_color $YELLOW "⚠️  Schema Registry PROD responded but with unexpected content: $prod_response"
    fi
fi

print_header "TEST ENVIRONMENT READY"

print_color $GREEN "🎉 Unified test environment is ready!"
print_color $WHITE ""

if [ "$FULL_STACK" = true ]; then
    print_color $CYAN "📊 Full Multi-Registry Environment:"
    print_color $WHITE "  🔧 DEV Environment:"
    print_color $WHITE "     • Kafka DEV:          localhost:9092"
    print_color $WHITE "     • Schema Registry DEV: localhost:38081"
    print_color $WHITE "  🏭 PROD Environment:"
    print_color $WHITE "     • Kafka PROD:         localhost:39093"
    print_color $WHITE "     • Schema Registry PROD: localhost:38082"
    print_color $WHITE "  🖥️  Management:"
    print_color $WHITE "     • AKHQ UI:            localhost:38080"
else
    print_color $CYAN "📊 Single-Registry Environment (DEV):"
    print_color $WHITE "  • Kafka DEV:          localhost:9092"
    print_color $WHITE "  • Schema Registry DEV: localhost:38081"
fi

print_color $WHITE ""
print_color $BLUE "🧪 Test Configuration:"
print_color $WHITE "  Single-registry tests: Use DEV registry (localhost:38081)"
print_color $WHITE "  Multi-registry tests:  Use both DEV + PROD registries"
print_color $WHITE ""
print_color $BLUE "▶️  Usage:"
print_color $WHITE "  • Run all tests:        ./run_all_tests.sh"
print_color $WHITE "  • Run specific test:    python test_specific.py"
print_color $WHITE "  • Check status:         $DOCKER_COMPOSE ps"
print_color $WHITE "  • View logs:            $DOCKER_COMPOSE logs -f"
print_color $WHITE "  • Stop environment:     ./stop_test_environment.sh"
print_color $WHITE ""
print_color $BLUE "🔄 Restart modes:"
print_color $WHITE "  • DEV only:             ./start_test_environment.sh dev"
print_color $WHITE "  • Full environment:     ./start_test_environment.sh multi"
print_color $WHITE "  • With UI:              ./start_test_environment.sh ui" 