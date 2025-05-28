#!/bin/bash

# Test Runner for Default Context "." Migration Tests
# 
# This script tests the specific scenario where bulk context migration
# was showing "0 subjects migrated" for the default context "." even
# though schemas were present. This addresses the sbt-jump issue.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 Default Context '.' Migration Test Runner"
echo "==========================================="
echo "Testing the fix for default context '.' migration issue"
echo "using simplified tests for better reliability"
echo "==========================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables for registry status
DEV_HEALTHY=false
PROD_HEALTHY=false

# Function to log with timestamp
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if multi-registry environment is running
check_registries() {
    log "Checking Schema Registry instances..."
    
    local registries=("http://localhost:38081" "http://localhost:38082")
    DEV_HEALTHY=false
    PROD_HEALTHY=false
    
    # Check dev registry (required)
    if curl -s -f "${registries[0]}/subjects" > /dev/null 2>&1; then
        success "✅ DEV Registry at ${registries[0]} is healthy"
        DEV_HEALTHY=true
    else
        error "❌ DEV Registry at ${registries[0]} is not responding"
    fi
    
    # Check prod registry (optional for multi-registry mode)
    if curl -s -f "${registries[1]}/subjects" > /dev/null 2>&1; then
        success "✅ PROD Registry at ${registries[1]} is healthy"
        PROD_HEALTHY=true
    else
        warning "⚠️  PROD Registry at ${registries[1]} is not responding"
    fi
    
    if [ "$DEV_HEALTHY" = false ]; then
        error "DEV registry is required but not healthy. Please start the test environment:"
        echo "  # For single registry:"
        echo "  cd tests && ./start_test_environment.sh"
        echo "  # For multi-registry:"
        echo "  cd tests && ./start_multi_registry_environment.sh"
        return 1
    fi
    
    if [ "$PROD_HEALTHY" = true ]; then
        log "Multi-registry environment detected (DEV + PROD)"
    else
        log "Single-registry environment detected (DEV only)"
        warning "Note: Some migration tests will run in single-registry mode"
    fi
    
    return 0
}

# Run the specific default context "." test
run_default_context_dot_test() {
    log "Running simplified default context '.' test..."
    
    cd "$PROJECT_ROOT"
    
    if python3 tests/test_default_context_dot_simple.py; then
        success "✅ Default context '.' test PASSED"
        return 0
    else
        error "❌ Default context '.' test FAILED"
        return 1
    fi
}

# Main test execution
main() {
    log "Starting simplified default context '.' tests..."
    
    # Check prerequisites
    if ! check_registries; then
        error "Registry health check failed"
        exit 1
    fi
    
    # Run the main test
    local tests_passed=0
    local total_tests=1
    
    echo ""
    log "=== Default Context '.' Simplified Test ==="
    if run_default_context_dot_test; then
        ((tests_passed++))
    fi
    
    # Summary
    echo ""
    echo "==========================================="
    log "Test Summary: $tests_passed/$total_tests tests passed"
    echo "==========================================="
    
    if [ $tests_passed -eq $total_tests ]; then
        success "🎉 DEFAULT CONTEXT '.' TEST PASSED!"
        echo ""
        success "✅ Basic default context '.' functionality is working"
        success "✅ URL building correctly handles context='.' parameter"
        success "✅ Subject listing works for default context"
        echo ""
        log "Test completed successfully"
        echo ""
        exit 0
    else
        error "⚠️  Default context '.' test failed"
        echo ""
        error "The default context '.' issue may not be fully resolved."
        error "Please check the error messages above for details."
        echo ""
        exit 1
    fi
}

# Handle script interruption
cleanup() {
    warning "Test execution interrupted"
    exit 130
}

trap cleanup SIGINT SIGTERM

# Run main function
main "$@" 