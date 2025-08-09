#!/bin/bash

# Script to run MCP Inspector tests for Kafka Schema Registry MCP Server
# Tests against released Docker images

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_VERSION="${DOCKER_VERSION:-stable}"
SKIP_ENV_SETUP="${SKIP_ENV_SETUP:-false}"
CLEANUP_AFTER="${CLEANUP_AFTER:-true}"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check if Schema Registry is running
check_schema_registry() {
    local port=$1
    local max_attempts=30
    local attempt=0
    
    print_status "Checking Schema Registry on port $port..."
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "http://localhost:$port" > /dev/null 2>&1; then
            print_status "Schema Registry is ready on port $port"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    
    print_error "Schema Registry failed to start on port $port"
    return 1
}

# Function to start test environment
start_test_environment() {
    if [ "$SKIP_ENV_SETUP" = "true" ]; then
        print_warning "Skipping environment setup (SKIP_ENV_SETUP=true)"
        return 0
    fi
    
    print_status "Starting test environment..."
    cd "$PROJECT_ROOT/tests"
    
    if [ -f "./start_test_environment.sh" ]; then
        ./start_test_environment.sh multi
        
        # Wait for all registries to be ready
        check_schema_registry 8081
        check_schema_registry 8091
        check_schema_registry 8092
        check_schema_registry 8093
    else
        print_error "Test environment setup script not found!"
        exit 1
    fi
}

# Function to stop test environment
stop_test_environment() {
    if [ "$CLEANUP_AFTER" = "false" ]; then
        print_warning "Keeping test environment running (CLEANUP_AFTER=false)"
        return 0
    fi
    
    print_status "Stopping test environment..."
    cd "$PROJECT_ROOT/tests"
    
    if [ -f "./stop_test_environment.sh" ]; then
        ./stop_test_environment.sh clean
    fi
}

# Function to run inspector tests
run_inspector_tests() {
    local config_file=$1
    local test_name=$2
    
    print_status "Running Inspector test: $test_name"
    print_status "Using Docker image: aywengo/kafka-schema-reg-mcp:$DOCKER_VERSION"
    
    cd "$SCRIPT_DIR"
    
    # Update config file to use the specified Docker version
    local temp_config="/tmp/inspector-config-temp.json"
    sed "s/:stable/:$DOCKER_VERSION/g" "$config_file" > "$temp_config"
    
    # Run the inspector
    npx @mcpjam/inspector --config "$temp_config"
    
    # Clean up temp file
    rm -f "$temp_config"
}

# Main execution
main() {
    print_status "Starting MCP Inspector tests for Kafka Schema Registry MCP"
    print_status "Docker version: $DOCKER_VERSION"
    
    # Change to inspector-tests directory
    cd "$SCRIPT_DIR"
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        print_status "Installing npm dependencies..."
        npm install
    fi
    
    # Start test environment
    start_test_environment
    
    # Run tests based on arguments
    if [ $# -eq 0 ]; then
        # Run all tests
        print_status "Running all Inspector tests..."
        run_inspector_tests "config/inspector-config-stable.json" "Single Registry"
        run_inspector_tests "config/inspector-config-multi-registry.json" "Multi Registry"
    else
        # Run specific test
        case "$1" in
            "single")
                run_inspector_tests "config/inspector-config-stable.json" "Single Registry"
                ;;
            "multi")
                run_inspector_tests "config/inspector-config-multi-registry.json" "Multi Registry"
                ;;
            "latest")
                DOCKER_VERSION="latest"
                run_inspector_tests "config/inspector-config-stable.json" "Latest Single Registry"
                ;;
            *)
                print_error "Unknown test type: $1"
                echo "Usage: $0 [single|multi|latest]"
                exit 1
                ;;
        esac
    fi
    
    # Stop test environment
    stop_test_environment
    
    print_status "Inspector tests completed!"
}

# Run main function
main "$@"
