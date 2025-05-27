#!/bin/bash

# Integration test runner for numbered environment variable configuration
# This script starts docker-compose services and runs comprehensive integration tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
MAX_WAIT_TIME=120

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check if Python is available
    if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
        log_error "Python is not installed or not in PATH"
        exit 1
    fi
    
    # Use python3 if available, otherwise python
    PYTHON_CMD="python3"
    if ! command -v python3 &> /dev/null; then
        PYTHON_CMD="python"
    fi
    
    # Check if required Python packages are installed
    if ! $PYTHON_CMD -c "import requests, mcp" &> /dev/null; then
        log_error "Required Python packages not installed. Run: pip install -r requirements.txt"
        exit 1
    fi
    
    log_success "Dependencies check passed"
}

start_services() {
    log_info "Starting docker-compose services..."
    
    # Change to project root for docker-compose commands
    cd "$PROJECT_ROOT"
    
    # Stop any existing services
    docker-compose down &> /dev/null || true
    
    # Start services
    docker-compose up -d
    
    log_success "Services started"
}

wait_for_services() {
    log_info "Waiting for services to be ready..."
    
    local start_time=$(date +%s)
    
    # Wait for Schema Registry
    log_info "Waiting for Schema Registry (http://localhost:38081)..."
    while true; do
        if curl -s -f http://localhost:38081/subjects &> /dev/null; then
            log_success "Schema Registry is ready"
            break
        fi
        
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $MAX_WAIT_TIME ]; then
            log_error "Services did not start within $MAX_WAIT_TIME seconds"
            show_service_logs
            exit 1
        fi
        
        sleep 2
    done
    
    # Additional wait to ensure full readiness
    log_info "Waiting additional 10 seconds for full service readiness..."
    sleep 10
    
    log_success "All services are ready"
}

show_service_logs() {
    log_warning "Showing service logs for debugging:"
    
    # Change to project root for docker-compose commands
    cd "$PROJECT_ROOT"
    
    echo "--- Schema Registry Logs ---"
    docker-compose logs schema-registry-mcp | tail -20
    echo "--- Kafka Logs ---"
    docker-compose logs kafka-mcp | tail -10
}

run_integration_tests() {
    log_info "Running numbered configuration integration tests..."
    
    cd "$SCRIPT_DIR"
    
    # Run the integration test
    if $PYTHON_CMD test_numbered_integration.py; then
        log_success "Integration tests completed successfully"
        return 0
    else
        log_error "Integration tests failed"
        return 1
    fi
}

cleanup_services() {
    local keep_running="$1"
    
    if [ "$keep_running" = "true" ]; then
        log_info "Keeping services running for manual testing"
        log_info "To stop services later, run: docker-compose down"
        return
    fi
    
    log_info "Stopping docker-compose services..."
    
    # Change to project root for docker-compose commands
    cd "$PROJECT_ROOT"
    docker-compose down
    
    log_success "Services stopped"
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Run integration tests for numbered environment variable configuration"
    echo ""
    echo "OPTIONS:"
    echo "  -k, --keep-running    Keep services running after tests"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                   Run tests and stop services"
    echo "  $0 --keep-running    Run tests and keep services for manual testing"
}

# Parse command line arguments
KEEP_RUNNING=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -k|--keep-running)
            KEEP_RUNNING=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    echo "🧪 Numbered Configuration Integration Test Runner"
    echo "================================================"
    echo ""
    
    # Trap to ensure cleanup on exit
    trap 'cleanup_services false' EXIT
    
    # Run all steps
    check_dependencies
    start_services
    wait_for_services
    
    # Run tests and capture result
    if run_integration_tests; then
        TEST_RESULT=0
    else
        TEST_RESULT=1
    fi
    
    # Cleanup based on options and test result
    if [ "$KEEP_RUNNING" = "true" ] || [ "$TEST_RESULT" -ne 0 ]; then
        cleanup_services "$KEEP_RUNNING"
    else
        cleanup_services false
    fi
    
    # Final result
    echo ""
    echo "================================================"
    if [ $TEST_RESULT -eq 0 ]; then
        log_success "All integration tests passed!"
        echo ""
        echo "📋 Tests Completed:"
        echo "   ✅ Single registry mode"
        echo "   ✅ Multi-registry mode with contexts" 
        echo "   ✅ Cross-registry operations"
        echo "   ✅ Per-registry READONLY mode"
        echo ""
        echo "🎯 Configuration Methods Tested:"
        echo "   ✅ Traditional environment variables"
        echo "   ✅ Numbered environment variables (X=1-8)"
        echo "   ✅ Per-registry READONLY controls"
    else
        log_error "Integration tests failed!"
        echo ""
        echo "🔍 Debug Information:"
        echo "   - Check service logs above"
        echo "   - Verify Schema Registry is accessible at http://localhost:38081"
        echo "   - Ensure Python dependencies are installed"
        if [ "$KEEP_RUNNING" = "true" ]; then
            echo "   - Services are still running for debugging"
        fi
    fi
    
    exit $TEST_RESULT
}

# Run main function
main "$@" 