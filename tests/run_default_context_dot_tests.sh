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
echo "where bulk migration showed '0 subjects migrated'"
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
    log "Running default context '.' migration test..."
    
    cd "$PROJECT_ROOT"
    
    if python3 tests/test_default_context_dot_migration.py; then
        success "✅ Default context '.' test PASSED"
        return 0
    else
        error "❌ Default context '.' test FAILED"
        return 1
    fi
}

# Run complementary URL building tests
run_url_building_verification() {
    log "Running URL building verification for default context..."
    
    cat > /tmp/test_url_building.py << 'EOF'
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import kafka_schema_registry_multi_mcp as mcp_server

# Setup test environment
os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
os.environ["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"

# Reinitialize registry manager
mcp_server.registry_manager._load_registries()

# Get client
client = mcp_server.registry_manager.get_registry("dev")

if client:
    # Test URL building
    url_none = client.build_context_url("/subjects", None)
    url_dot = client.build_context_url("/subjects", ".")
    url_production = client.build_context_url("/subjects", "production")
    
    print(f"URL with context=None: {url_none}")
    print(f"URL with context='.': {url_dot}")
    print(f"URL with context='production': {url_production}")
    
    # Verify the fix
    if url_none == url_dot:
        print("✅ SUCCESS: context=None and context='.' produce same URL")
        sys.exit(0)
    else:
        print("❌ FAILURE: context=None and context='.' produce different URLs")
        sys.exit(1)
else:
    print("❌ Could not get registry client")
    sys.exit(1)
EOF

    if python3 /tmp/test_url_building.py; then
        success "✅ URL building verification PASSED"
        rm -f /tmp/test_url_building.py
        return 0
    else
        error "❌ URL building verification FAILED"
        rm -f /tmp/test_url_building.py
        return 1
    fi
}

# Main test execution
main() {
    log "Starting default context '.' migration tests..."
    
    # Check prerequisites
    if ! check_registries; then
        error "Registry health check failed"
        exit 1
    fi
    
    # Run tests
    local tests_passed=0
    local total_tests=2
    
    echo ""
    log "=== Test 1: URL Building Verification ==="
    if run_url_building_verification; then
        ((tests_passed++))
    fi
    
    echo ""
    log "=== Test 2: Default Context '.' Migration ==="
    if run_default_context_dot_test; then
        ((tests_passed++))
    fi
    
    # Summary
    echo ""
    echo "==========================================="
    log "Test Summary: $tests_passed/$total_tests tests passed"
    echo "==========================================="
    
    if [ $tests_passed -eq $total_tests ]; then
        success "🎉 ALL DEFAULT CONTEXT '.' TESTS PASSED!"
        echo ""
        success "✅ The default context '.' migration bug has been fixed"
        success "✅ Bulk context migration now properly detects schemas in default context"
        success "✅ URL building correctly handles context='.' parameter"
        echo ""
        log "The fix ensures that:"
        echo "  • context='.' is treated the same as context=None"
        echo "  • migrate_context('.' , ...) finds and migrates schemas"
        echo "  • build_context_url handles default context correctly"
        echo ""
        log "Test completed in $([ "$PROD_HEALTHY" = true ] && echo "multi-registry" || echo "single-registry") mode"
        echo ""
        exit 0
    else
        error "⚠️  $((total_tests - tests_passed)) test(s) failed"
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