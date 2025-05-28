#!/bin/bash

# Multi-Registry Batch Cleanup Tests Runner
# 
# This script runs batch cleanup tests specifically for multi-registry environments,
# testing both kafka_schema_registry_mcp.py and kafka_schema_registry_multi_mcp.py
# in a multi-registry context.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🧹 Kafka Schema Registry Multi-Registry Batch Cleanup Test Suite"
echo "================================================================"
echo "Testing batch cleanup functionality in multi-registry environment:"
echo "• Single-Registry Mode (kafka_schema_registry_mcp.py)"
echo "• Multi-Registry Mode (kafka_schema_registry_multi_mcp.py)"
echo "• Cross-Registry Batch Operations"
echo "• Safety Features (dry_run=True by default)"
echo "• Performance and Concurrency"
echo "================================================================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Global variables
DEV_HEALTHY=false
PROD_HEALTHY=false
TESTS_PASSED=0
TOTAL_TESTS=0
FAILED_TESTS=()
TEST_START_TIME=$(date +%s)

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

info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

header() {
    echo ""
    echo -e "${BOLD}${CYAN}=======================================${NC}"
    echo -e "${BOLD}${CYAN} $1${NC}"
    echo -e "${BOLD}${CYAN}=======================================${NC}"
}

# Check if multi-registry environment is available
check_multi_registry_environment() {
    log "Checking multi-registry environment..."
    
    local dev_url="http://localhost:38081"
    local prod_url="http://localhost:38082"
    
    # Check dev registry
    if curl -s -f "${dev_url}/subjects" > /dev/null 2>&1; then
        success "✅ DEV Registry at ${dev_url} is healthy"
        DEV_HEALTHY=true
    else
        error "❌ DEV Registry at ${dev_url} is not responding"
    fi
    
    # Check prod registry
    if curl -s -f "${prod_url}/subjects" > /dev/null 2>&1; then
        success "✅ PROD Registry at ${prod_url} is healthy"
        PROD_HEALTHY=true
    else
        error "❌ PROD Registry at ${prod_url} is not responding"
    fi
    
    if [ "$DEV_HEALTHY" = false ] || [ "$PROD_HEALTHY" = false ]; then
        error "Multi-registry environment is not fully healthy!"
        echo ""
        warning "To start the multi-registry environment:"
        echo "  cd tests && ./start_multi_registry_environment.sh"
        echo ""
        return 1
    fi
    
    success "🎉 Multi-registry environment is ready!"
    return 0
}

# Run a test and track results
run_test() {
    local test_name="$1"
    local test_command="$2"
    local description="$3"
    
    header "Running: $test_name"
    info "Description: $description"
    log "Executing: $test_command"
    
    ((TOTAL_TESTS++))
    
    local start_time=$(date +%s)
    
    if eval "$test_command"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        success "✅ $test_name PASSED (${duration}s)"
        ((TESTS_PASSED++))
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        error "❌ $test_name FAILED (${duration}s)"
        FAILED_TESTS+=("$test_name")
        return 1
    fi
}

# Test 1: Single-Registry Batch Cleanup in Multi-Registry Environment
test_single_registry_batch_cleanup() {
    log "Testing single-registry batch cleanup with multi-registry environment running..."
    
    # Set environment for single-registry mode
    export SCHEMA_REGISTRY_URL="http://localhost:38081"
    export READONLY="false"
    
    # Run the comprehensive integration tests
    if [ -f "tests/test_batch_cleanup_integration.py" ]; then
        python3 -m pytest tests/test_batch_cleanup_integration.py::TestBatchCleanupIntegration::test_dry_run_default_safety -v
        python3 -m pytest tests/test_batch_cleanup_integration.py::TestBatchCleanupIntegration::test_explicit_dry_run_false -v
        python3 -m pytest tests/test_batch_cleanup_integration.py::TestBatchCleanupIntegration::test_empty_context_handling -v
        python3 -m pytest tests/test_batch_cleanup_integration.py::TestBatchCleanupIntegration::test_readonly_mode_protection -v
        python3 -m pytest tests/test_batch_cleanup_integration.py::TestBatchCleanupIntegration::test_large_context_performance -v
        return $?
    else
        error "test_batch_cleanup_integration.py not found"
        return 1
    fi
}

# Test 2: Multi-Registry Batch Cleanup
test_multi_registry_batch_cleanup() {
    log "Testing multi-registry batch cleanup operations..."
    
    # Set multi-registry environment variables
    export SCHEMA_REGISTRY_NAME_1="dev"
    export SCHEMA_REGISTRY_URL_1="http://localhost:38081"
    export SCHEMA_REGISTRY_NAME_2="prod"
    export SCHEMA_REGISTRY_URL_2="http://localhost:38082"
    export READONLY="false"
    
    # Run multi-registry specific tests
    if [ -f "tests/test_batch_cleanup_integration.py" ]; then
        python3 -m pytest tests/test_batch_cleanup_integration.py::TestBatchCleanupIntegration::test_multi_registry_dry_run_default -v
        python3 -m pytest tests/test_batch_cleanup_integration.py::TestBatchCleanupIntegration::test_cross_registry_operations -v
        python3 -m pytest tests/test_batch_cleanup_integration.py::TestBatchCleanupIntegration::test_error_recovery_and_reporting -v
        return $?
    else
        error "test_batch_cleanup_integration.py not found"
        return 1
    fi
}

# Test 3: Original Batch Cleanup Tests
test_original_batch_cleanup() {
    log "Running original batch cleanup tests..."
    
    if [ -f "tests/test_batch_cleanup.py" ]; then
        python3 tests/test_batch_cleanup.py
        return $?
    else
        warning "test_batch_cleanup.py not found, skipping"
        return 0
    fi
}

# Test 4: Cross-Registry Batch Operations
test_cross_registry_batch_operations() {
    log "Testing cross-registry batch operations..."
    
    # Run the test directly from the project root
    cd "$PROJECT_ROOT"
    
    # Create a Python test script inline
    python3 << 'EOF'
#!/usr/bin/env python3
import sys
import os
import uuid

# Set up multi-registry environment
os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
os.environ["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
os.environ["SCHEMA_REGISTRY_NAME_2"] = "prod"
os.environ["SCHEMA_REGISTRY_URL_2"] = "http://localhost:38082"

import kafka_schema_registry_multi_mcp as multi_mcp

def test_cross_registry_dry_run():
    """Test that cross-registry operations default to dry_run=True"""
    context_name = f"test-cross-{uuid.uuid4().hex[:8]}"
    
    # Test cross-registry cleanup
    result = multi_mcp.clear_context_across_registries_batch(
        context=context_name,
        registries=["dev", "prod"]
    )
    
    assert result["dry_run"] == True, "Cross-registry should default to dry_run=True"
    assert result["registries_targeted"] == 2, "Should target both registries"
    print("✅ Cross-registry operations default to dry_run=True")
    
    # Test with explicit dry_run=False (but with non-existent context for safety)
    result = multi_mcp.clear_context_across_registries_batch(
        context=f"nonexistent-{uuid.uuid4().hex[:8]}",
        registries=["dev", "prod"],
        dry_run=False
    )
    
    assert result["dry_run"] == False, "Should respect explicit dry_run=False"
    print("✅ Cross-registry operations respect explicit dry_run setting")
    
    return True

def test_registry_validation():
    """Test registry validation in batch operations"""
    # Test with invalid registry
    result = multi_mcp.clear_context_batch(
        context="test-invalid",
        registry="nonexistent-registry",
        dry_run=True
    )
    
    assert "error" in result, "Should handle invalid registry"
    assert "not found" in result["error"], "Should provide helpful error"
    print("✅ Invalid registry handled gracefully")
    
    # Test with valid registry
    result = multi_mcp.clear_context_batch(
        context="test-valid",
        registry="dev",
        dry_run=True
    )
    
    assert "error" not in result, "Should work with valid registry"
    assert result["registry"] == "dev", "Should use specified registry"
    print("✅ Valid registry operations work correctly")
    
    return True

if __name__ == "__main__":
    try:
        test_cross_registry_dry_run()
        test_registry_validation()
        print("🎉 All cross-registry batch tests passed!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Cross-registry batch tests failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
EOF
    
    local result=$?
    cd "$SCRIPT_DIR"
    return $result
}

# Test 5: Performance and Concurrency
test_performance_and_concurrency() {
    log "Testing batch cleanup performance and concurrency..."
    
    # Run performance-related tests from the integration test suite
    cd "$PROJECT_ROOT"
    
    # Run specific performance tests
    SCHEMA_REGISTRY_URL=http://localhost:38081 \
    python3 -m pytest tests/test_batch_cleanup_integration.py::TestBatchCleanupIntegration::test_large_context_performance -v
    local result1=$?
    
    SCHEMA_REGISTRY_URL=http://localhost:38081 \
    python3 -m pytest tests/test_batch_cleanup_integration.py::TestBatchCleanupIntegration::test_concurrent_cleanup_operations -v
    local result2=$?
    
    SCHEMA_REGISTRY_URL=http://localhost:38081 \
    python3 -m pytest tests/test_batch_cleanup_integration.py::TestBatchCleanupIntegration::test_comprehensive_reporting_metrics -v
    local result3=$?
    
    cd "$SCRIPT_DIR"
    
    # Return success if all tests passed
    if [ $result1 -eq 0 ] && [ $result2 -eq 0 ] && [ $result3 -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

# Main test execution
main() {
    log "Starting multi-registry batch cleanup test suite..."
    
    # Prerequisites check
    if ! check_multi_registry_environment; then
        error "Cannot proceed without healthy multi-registry environment"
        exit 1
    fi
    
    echo ""
    info "🚀 Running Multi-Registry Batch Cleanup Test Suite"
    info "Total test categories: 5"
    echo ""
    
    # Run all test categories
    run_test \
        "Single-Registry Batch Cleanup" \
        "test_single_registry_batch_cleanup" \
        "Testing single-registry batch cleanup with multi-registry environment"
    
    run_test \
        "Multi-Registry Batch Cleanup" \
        "test_multi_registry_batch_cleanup" \
        "Testing multi-registry specific batch cleanup operations"
    
    run_test \
        "Original Batch Cleanup Tests" \
        "test_original_batch_cleanup" \
        "Running original batch cleanup test suite for compatibility"
    
    run_test \
        "Cross-Registry Batch Operations" \
        "test_cross_registry_batch_operations" \
        "Testing batch operations across multiple registries"
    
    run_test \
        "Performance and Concurrency" \
        "test_performance_and_concurrency" \
        "Testing batch cleanup performance and concurrent operations"
    
    # Generate test summary
    generate_test_summary
}

# Generate comprehensive test summary
generate_test_summary() {
    local end_time=$(date +%s)
    local total_duration=$((end_time - TEST_START_TIME))
    local minutes=$((total_duration / 60))
    local seconds=$((total_duration % 60))
    
    echo ""
    echo "=============================================="
    echo -e "${BOLD}${CYAN}BATCH CLEANUP TEST SUMMARY${NC}"
    echo "=============================================="
    echo ""
    
    # Overall Results
    echo -e "${BOLD}OVERALL RESULTS:${NC}"
    echo "  Tests Passed: ${TESTS_PASSED}/${TOTAL_TESTS}"
    echo "  Success Rate: $(( TESTS_PASSED * 100 / TOTAL_TESTS ))%"
    echo "  Total Duration: ${minutes}m ${seconds}s"
    echo ""
    
    # Pass/Fail Status
    if [ ${TESTS_PASSED} -eq ${TOTAL_TESTS} ]; then
        echo -e "${GREEN}${BOLD}🎉 ALL BATCH CLEANUP TESTS PASSED!${NC}"
        echo ""
        success "✅ Single-registry batch cleanup works correctly"
        success "✅ Multi-registry batch cleanup functions properly"
        success "✅ Cross-registry operations validated"
        success "✅ Safety features (dry_run=True) confirmed"
        success "✅ Performance and concurrency validated"
        success "✅ Error handling is robust"
        echo ""
        
        echo -e "${CYAN}${BOLD}VALIDATED FEATURES:${NC}"
        echo "  • Batch Context Cleanup (Single & Multi-Registry)"
        echo "  • Default dry_run=True Safety Feature"
        echo "  • Cross-Registry Batch Operations"
        echo "  • Parallel Execution (10 concurrent deletions)"
        echo "  • Comprehensive Error Reporting"
        echo "  • READONLY Mode Protection"
        echo "  • Performance Optimization"
        echo "  • Multi-Context Batch Operations"
        echo ""
        
        success "🚀 Batch cleanup tools are production-ready!"
        echo ""
        exit 0
        
    else
        echo -e "${RED}${BOLD}❌ SOME BATCH CLEANUP TESTS FAILED${NC}"
        echo ""
        error "Failed Tests:"
        for failed_test in "${FAILED_TESTS[@]}"; do
            echo "  • $failed_test"
        done
        echo ""
        
        warning "Please review the failed tests above and check:"
        echo "  1. Multi-registry environment health"
        echo "  2. Registry connectivity"
        echo "  3. Python dependencies"
        echo "  4. Test data setup"
        echo ""
        
        error "Batch cleanup functionality may have issues!"
        exit 1
    fi
}

# Handle script interruption
cleanup() {
    warning "Batch cleanup test execution interrupted"
    echo ""
    if [ ${TOTAL_TESTS} -gt 0 ]; then
        warning "Partial results: ${TESTS_PASSED}/${TOTAL_TESTS} tests passed"
    fi
    exit 130
}

trap cleanup SIGINT SIGTERM

# Script usage information
usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Multi-Registry Batch Cleanup Test Runner"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  --quick        Run only essential tests (not implemented)"
    echo "  --full         Run all tests (default)"
    echo ""
    echo "Prerequisites:"
    echo "  • Multi-registry environment running on ports 38081-38082"
    echo "  • Start with: ./start_multi_registry_environment.sh"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run all batch cleanup tests"
    echo "  $0 --help            # Show this help"
    echo ""
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        usage
        exit 0
        ;;
    --quick)
        warning "Quick mode not yet implemented, running full test suite"
        ;;
    --full|"")
        # Default behavior
        ;;
    *)
        error "Unknown option: $1"
        usage
        exit 1
        ;;
esac

# Run main function
main "$@" 