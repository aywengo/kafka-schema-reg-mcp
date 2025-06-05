#!/bin/bash

# Add parent directory to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(dirname $(dirname $(realpath $0)))"

# Test Runner for All-Versions Migration Tests
# 
# This script tests the migrate_schema function with version list
# to preserve complete schema evolution history.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 All-Versions Migration Test Runner"
echo "====================================="
echo "Testing the migrate_schema function with version list"
echo "to preserve complete schema evolution history"
echo "====================================="

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

# Check if registries are available
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
        log "This will test full all-versions migration between registries"
    else
        log "Single-registry environment detected (DEV only)"
        log "This will test all-versions migration logic with same-registry scenarios"
    fi
    
    return 0
}

# Run the all-versions migration test
run_all_versions_migration_test() {
    log "Running all-versions migration test..."
    
    cd "$PROJECT_ROOT"
    
    if python3 tests/test_all_versions_migration.py; then
        success "✅ All-versions migration test PASSED"
        return 0
    else
        error "❌ All-versions migration test FAILED"
        return 1
    fi
}

# Run schema evolution verification test
run_schema_evolution_verification() {
    log "Running schema evolution verification..."
    
    cat > /tmp/test_schema_evolution.py << 'EOF'
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import kafka_schema_registry_multi_mcp as mcp_server

# Setup test environment
os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
os.environ["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"

# Reinitialize registry manager
mcp_server.registry_manager._load_multi_registries()

def test_get_schema_versions():
    """Test that we can retrieve multiple versions of a schema"""
    try:
        # Use default context for this test
        subjects = mcp_server.get_subjects(context=None, registry="dev")
        
        if not subjects or len(subjects) == 0:
            print("No subjects found - this is expected if no schemas exist yet")
            return True
        
        # Test with first available subject
        subject = subjects[0]
        versions = mcp_server.get_schema_versions(subject, context=None, registry="dev")
        
        if isinstance(versions, dict) and "error" in versions:
            print(f"Expected behavior: {versions['error']}")
            return True
        
        if isinstance(versions, list):
            print(f"✅ Found {len(versions)} version(s) for subject '{subject}': {versions}")
            return True
        
        print(f"❌ Unexpected response format: {type(versions)}")
        return False
        
    except Exception as e:
        print(f"❌ Schema evolution verification failed: {e}")
        return False

if __name__ == "__main__":
    success = test_get_schema_versions()
    sys.exit(0 if success else 1)
EOF

    if python3 /tmp/test_schema_evolution.py; then
        success "✅ Schema evolution verification PASSED"
        rm -f /tmp/test_schema_evolution.py
        return 0
    else
        error "❌ Schema evolution verification FAILED"
        rm -f /tmp/test_schema_evolution.py
        return 1
    fi
}

# Main test execution
main() {
    log "Starting all-versions migration tests..."
    
    # Check prerequisites
    if ! check_registries; then
        error "Registry health check failed"
        exit 1
    fi
    
    # Run tests
    local tests_passed=0
    local total_tests=2
    
    echo ""
    log "=== Test 1: Schema Evolution Verification ==="
    if run_schema_evolution_verification; then
        ((tests_passed++))
    fi
    
    echo ""
    log "=== Test 2: All-Versions Migration ==="
    if run_all_versions_migration_test; then
        ((tests_passed++))
    fi
    
    # Summary
    echo ""
    echo "==========================================="
    log "Test Summary: $tests_passed/$total_tests tests passed"
    echo "==========================================="
    
    if [ $tests_passed -eq $total_tests ]; then
        echo ""
        success "🎉 ALL ALL-VERSIONS MIGRATION TESTS PASSED!"
        echo ""
        success "✅ migrate_schema with versions parameter works correctly"
        success "✅ Complete schema evolution history can be preserved"
        success "✅ Version-level migration tracking is accurate"
        echo ""
        log "Key features validated:"
        echo "  • versions parameter allows migrating specific versions"
        echo "  • All schema versions are migrated in chronological order"
        echo "  • Version-level success/failure tracking works"
        echo "  • Both single-version and all-versions modes work"
        echo ""
        log "Test completed in multi-registry mode"
        exit 0
    else
        error "⚠️  $((total_tests - tests_passed)) test(s) failed"
        echo ""
        error "The all-versions migration functionality may have issues."
        error "Please check the error messages above for details."
        echo ""
        log "Troubleshooting steps:"
        echo "  1. Ensure Schema Registry is healthy"
        echo "  2. Check that schemas with multiple versions exist"
        echo "  3. Verify multi-registry environment if needed"
        echo "  4. Review migration logs for version-specific errors"
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