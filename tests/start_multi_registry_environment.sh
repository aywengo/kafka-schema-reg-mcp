#!/bin/bash

# Multi-Registry Environment Startup Script
# Comprehensive multi-registry environment with 2 Kafka clusters and 2 Schema Registries

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

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_color $CYAN "🚀 Multi-Registry Environment Startup"
print_color $CYAN "=====================================\n"

# Check Docker
print_color $BLUE "🔍 Checking Docker..."
if ! command -v docker &> /dev/null; then
    print_color $RED "❌ Docker is not installed"
    exit 1
fi

if ! docker info &> /dev/null; then
    print_color $RED "❌ Docker is not running"
    exit 1
fi

print_color $GREEN "✅ Docker is ready"

# Complete cleanup first
print_color $YELLOW "🧹 Performing complete cleanup..."
docker stop kafka-dev kafka-prod schema-registry-dev schema-registry-prod akhq-multi mcp-server-multi 2>/dev/null || true
docker rm kafka-dev kafka-prod schema-registry-dev schema-registry-prod akhq-multi mcp-server-multi 2>/dev/null || true
docker network rm tests_kafka-multi-test 2>/dev/null || true
docker volume prune -f &>/dev/null || true

# Check port availability
print_color $BLUE "🔍 Checking port availability..."
ports=(38080 38081 38082 39092 39093 39094 39095)
for port in "${ports[@]}"; do
    if lsof -i :$port &> /dev/null; then
        print_color $RED "❌ Port $port is in use"
        print_color $YELLOW "Please stop the service using this port and try again"
        exit 1
    fi
done
print_color $GREEN "✅ All required ports are available"

# Start services
print_color $BLUE "🚀 Starting Multi-Registry environment..."
print_color $WHITE "   This includes: 2 Kafka clusters, 2 Schema Registries, AKHQ UI, MCP Server"

cd "$SCRIPT_DIR"

# Build the image first
print_color $BLUE "🔨 Building MCP server image..."
docker-compose -f docker-compose.multi-test.yml build mcp-server-multi

# Start services
print_color $BLUE "Starting containers..."
docker-compose -f docker-compose.multi-test.yml up -d

# Wait a moment for containers to initialize
sleep 10

# Wait for services to be ready
print_color $BLUE "⏳ Waiting for services to be ready..."

# Wait for Kafka DEV  
print_color $BLUE "Waiting for Kafka DEV (localhost:9092)..."
for i in {1..30}; do
    if docker exec kafka-dev kafka-topics --bootstrap-server localhost:9092 --list &>/dev/null; then
        print_color $GREEN "✅ Kafka DEV is ready"
        break
    fi
    sleep 2
    if [ $i -eq 30 ]; then
        print_color $RED "❌ Kafka DEV failed to start"
        docker logs kafka-dev --tail 20
        exit 1
    fi
done

# Wait for Kafka PROD  
print_color $BLUE "Waiting for Kafka PROD (localhost:9093)..."
for i in {1..30}; do
    if docker exec kafka-prod kafka-topics --bootstrap-server localhost:9093 --list &>/dev/null; then
        print_color $GREEN "✅ Kafka PROD is ready"
        break
    fi
    sleep 2
    if [ $i -eq 30 ]; then
        print_color $RED "❌ Kafka PROD failed to start"
        docker logs kafka-prod --tail 20
        exit 1
    fi
done

# Wait for Schema Registry DEV
print_color $BLUE "Waiting for Schema Registry DEV (localhost:38081)..."
for i in {1..30}; do
    if curl -s http://localhost:38081/subjects &>/dev/null; then
        print_color $GREEN "✅ Schema Registry DEV is ready"
        break
    fi
    sleep 2
    if [ $i -eq 30 ]; then
        print_color $RED "❌ Schema Registry DEV failed to start"
        docker logs schema-registry-dev --tail 20
        exit 1
    fi
done

# Wait for Schema Registry PROD
print_color $BLUE "Waiting for Schema Registry PROD (localhost:38082)..."
for i in {1..30}; do
    if curl -s http://localhost:38082/subjects &>/dev/null; then
        print_color $GREEN "✅ Schema Registry PROD is ready"
        break
    fi
    sleep 2
    if [ $i -eq 30 ]; then
        print_color $RED "❌ Schema Registry PROD failed to start"
        docker logs schema-registry-prod --tail 20
        exit 1
    fi
done

# Wait for AKHQ UI
print_color $BLUE "Waiting for AKHQ UI (localhost:38080)..."
for i in {1..30}; do
    if curl -s http://localhost:38080/api/health &>/dev/null; then
        print_color $GREEN "✅ AKHQ UI is ready"
        break
    fi
    sleep 2
    if [ $i -eq 30 ]; then
        print_color $RED "❌ AKHQ UI failed to start"
        docker logs akhq-multi --tail 20
        exit 1
    fi
done

print_color $GREEN "\n🎉 Multi-Registry environment is ready!"
print_color $WHITE "===================================================="
print_color $CYAN "📊 Service URLs:"
print_color $WHITE "   • AKHQ UI:               http://localhost:38080"
print_color $WHITE "   • Schema Registry DEV:   http://localhost:38081"
print_color $WHITE "   • Schema Registry PROD:  http://localhost:38082"
print_color $WHITE "   • Kafka DEV:             localhost:39092"
print_color $WHITE "   • Kafka PROD:            localhost:39093"
print_color $WHITE ""
print_color $CYAN "🔧 Registry Configuration:"
print_color $WHITE "   • DEV: Read-Write, Backward compatibility"
print_color $WHITE "   • PROD: Read-Only, Forward compatibility"
print_color $WHITE ""
print_color $CYAN "▶️  Next Steps:"
print_color $WHITE "   • Run tests: ./run_multi_registry_tests.sh"
print_color $WHITE "   • Check status: docker-compose -f docker-compose.multi-test.yml ps"
print_color $WHITE "   • View logs: docker-compose -f docker-compose.multi-test.yml logs -f"
print_color $WHITE "====================================================" 