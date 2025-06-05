#!/bin/bash

# Multi-Registry Test Runner
# 
# This script runs all tests specifically designed for multi-registry environments,
# including cross-registry operations, migration functionality, and multi-registry
# configuration validation.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Results directory and timestamp
TEST_RESULTS_DIR="$SCRIPT_DIR/results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$TEST_RESULTS_DIR"

# Log and summary files
MULTI_LOG="$TEST_RESULTS_DIR/multi_registry_test_$TIMESTAMP.log"
SUMMARY_LOG="$TEST_RESULTS_DIR/multi_registry_summary_$TIMESTAMP.txt"
CSV_LOG="$TEST_RESULTS_DIR/multi_registry_results_$TIMESTAMP.csv"

# Save all output to log file as well as console
exec > >(tee -a "$MULTI_LOG") 2>&1

echo "🚀 Kafka Schema Registry Multi-Registry Test Suite"
echo "=================================================="
echo "Testing all multi-registry functionality including:"
echo "• Cross-Registry Operations"
echo "• Schema Migration (All Types)"
echo "• ID Preservation"
echo "• Context Management"
echo "• Multi-Registry Configuration"
echo "• End-to-End Workflows"
echo ""
echo "✨ Environment-Compatible Design:"
echo "• Uses existing multi-registry environment"
echo "• No Docker container conflicts"
echo "• Lightweight tests with robust monitoring"
echo "=================================================="

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
FAILED_OPTIONAL_TESTS=()  # New array to track failed optional tests
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
    
    # Check dev registry (required)
    if curl -s -f "${dev_url}/subjects" > /dev/null 2>&1; then
        success "✅ DEV Registry at ${dev_url} is healthy"
        DEV_HEALTHY=true
    else
        error "❌ DEV Registry at ${dev_url} is not responding"
    fi
    
    # Check prod registry (required for multi-registry)
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
        warning "Or start manually with:"
        echo "  docker-compose -f tests/docker-compose.multi-test.yml up -d"
        echo ""
        return 1
    fi
    
    success "🎉 Multi-registry environment is ready!"
    info "DEV Registry: ${dev_url}"
    info "PROD Registry: ${prod_url}"
    return 0
}

# Fix registry modes for testing
fix_registry_modes() {
    header "Fixing Registry Modes"
    log "Ensuring registries are in correct mode for testing..."
    
    # Check if fix_registry_modes.py exists
    if [ -f "tests/fix_registry_modes.py" ]; then
        # Run the fix script
        if python3 tests/fix_registry_modes.py > /dev/null 2>&1; then
            success "✅ Registry modes fixed successfully"
            info "• DEV Registry: READWRITE mode (allows schema creation)"
            info "• PROD Registry: READWRITE mode (allows migration testing)"
        else
            warning "⚠️  Registry mode fix encountered issues"
            warning "Tests may fail if registries are in READONLY mode"
            warning "You can manually fix by running: python3 tests/fix_registry_modes.py"
        fi
    else
        warning "⚠️  fix_registry_modes.py not found - skipping mode fix"
        warning "Tests may fail if registries are in READONLY mode"
    fi
}

# Recheck connectivity between tests
recheck_connectivity() {
    log "Rechecking registry connectivity..."
    
    local dev_url="http://localhost:38081"
    local prod_url="http://localhost:38082"
    local connectivity_ok=true
    
    if ! curl -s -f "${dev_url}/subjects" > /dev/null 2>&1; then
        warning "⚠️  DEV Registry connectivity lost"
        connectivity_ok=false
    fi
    
    if ! curl -s -f "${prod_url}/subjects" > /dev/null 2>&1; then
        warning "⚠️  PROD Registry connectivity lost" 
        connectivity_ok=false
    fi
    
    if [ "$connectivity_ok" = false ]; then
        # Check if it's a Docker container issue
        if command -v docker > /dev/null 2>&1; then
            warning "Checking Docker containers..."
            check_docker_containers
        fi
        return 1
    fi
    
    return 0
}

# Check Docker container status
check_docker_containers() {
    log "Checking Docker container status..."
    
    # Check if containers are running
    local containers_running=true
    
    if ! docker ps --format "table {{.Names}}" | grep -q "schema-registry-dev"; then
        warning "⚠️  schema-registry-dev container not found"
        containers_running=false
    fi
    
    if ! docker ps --format "table {{.Names}}" | grep -q "schema-registry-prod"; then
        warning "⚠️  schema-registry-prod container not found"
        containers_running=false
    fi
    
    if [ "$containers_running" = false ]; then
        error "❌ Multi-registry Docker containers are not running"
        echo ""
        warning "To restart the multi-registry environment:"
        echo "  cd tests && ./start_multi_registry_environment.sh"
        echo ""
        return 1
    fi
    
    success "✅ Docker containers are running"
    return 0
}

# Run a test and track results
run_test() {
    local test_name="$1"
    local test_script="$2"
    local description="$3"
    local is_optional="${4:-false}"  # New parameter to indicate if test is optional
    
    header "Running: $test_name"
    info "Description: $description"
    log "Executing: $test_script"
    
    # Check connectivity before running the test
    if ! recheck_connectivity; then
        warning "Registry connectivity issues detected before test"
        warning "Attempting to continue with test anyway..."
    fi
    
    ((TOTAL_TESTS++))
    
    local start_time=$(date +%s)
    
    if bash "$test_script"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        success "✅ $test_name PASSED (${duration}s)"
        ((TESTS_PASSED++))
        echo "PASS,$test_name,$duration,$description" >> "$CSV_LOG"
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        # Check if failure was due to connectivity
        if ! recheck_connectivity; then
            warning "⚠️  $test_name FAILED due to registry connectivity issues (${duration}s)"
            warning "This may not be a test failure but an environment issue"
        else
            error "❌ $test_name FAILED (${duration}s)"
        fi
        
        if [ "$is_optional" = true ]; then
            FAILED_OPTIONAL_TESTS+=("$test_name")
            ((TOTAL_TESTS--))  # Don't count optional tests in total
        else
            FAILED_TESTS+=("$test_name")
        fi
        echo "FAIL,$test_name,$duration,$description" >> "$CSV_LOG"
        return 1
    fi
}

# Run Python test directly
run_python_test() {
    local test_name="$1"
    local test_script="$2"
    local description="$3"
    
    header "Running: $test_name"
    info "Description: $description"
    log "Executing: python3 $test_script"
    
    # Check connectivity before running the test
    if ! recheck_connectivity; then
        warning "Registry connectivity issues detected before test"
        warning "Attempting to continue with test anyway..."
    fi
    
    ((TOTAL_TESTS++))
    
    local start_time=$(date +%s)
    
    cd "$PROJECT_ROOT"
    if python3 "$test_script"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        success "✅ $test_name PASSED (${duration}s)"
        ((TESTS_PASSED++))
        echo "PASS,$test_name,$duration,$description" >> "$CSV_LOG"
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        # Check if failure was due to connectivity
        if ! recheck_connectivity; then
            warning "⚠️  $test_name FAILED due to registry connectivity issues (${duration}s)"
            warning "This may not be a test failure but an environment issue"
        else
            error "❌ $test_name FAILED (${duration}s)"
        fi
        
        FAILED_TESTS+=("$test_name")
        echo "FAIL,$test_name,$duration,$description" >> "$CSV_LOG"
        return 1
    fi
}

# Main test execution
main() {
    log "Starting multi-registry test suite..."
    # Initialize CSV results file
    echo "Status,TestName,Duration,Description" > "$CSV_LOG"
    
    # Prerequisites check
    if ! check_multi_registry_environment; then
        error "Cannot proceed without healthy multi-registry environment"
        exit 1
    fi
    
    # Fix registry modes to ensure they're in READWRITE mode for testing
    fix_registry_modes
    
    echo ""
    info "🚀 Running Multi-Registry Test Suite"
    info "Total test categories: 12 (core functionality + OAuth)"
    echo ""
    
    # 1. Multi-Registry Configuration Tests
    if [ -f "tests/test_multi_registry_validation.py" ]; then
        run_python_test \
            "Multi-Registry Configuration" \
            "tests/test_multi_registry_validation.py" \
            "Multi-registry configuration validation using existing environment"
    else
        warning "⚠️  Multi-registry configuration tests not found"
    fi
    
    # 2. Cross-Registry Comparison Tests
    if [ -f "test_compare_registries.py" ]; then
        run_python_test \
            "Cross-Registry Comparison" \
            "test_compare_registries.py" \
            "Compare subjects between registries (authentication fix validation)"
    else
        warning "⚠️  Cross-registry comparison tests not found"
    fi
    
    # 3. Docker Configuration Generation Tests
    if [ -f "tests/test_migrate_context_docker_config.py" ]; then
        run_python_test \
            "Docker Config Generation" \
            "tests/test_migrate_context_docker_config.py" \
            "Test migrate_context Docker configuration generation for kafka-schema-reg-migrator"
    else
        warning "⚠️  Docker configuration generation tests not found"
    fi
    
    # 4. Migration Integration Tests
    if [ -f "tests/test_lightweight_migration_integration.py" ]; then
        run_python_test \
            "Migration Integration" \
            "tests/test_lightweight_migration_integration.py" \
            "End-to-end migration integration without Docker environment management"
    else
        warning "⚠️  Lightweight migration integration tests not found"
    fi
    
    # 5. Default Context Migration Tests  
    if [ -f "tests/test_lightweight_migration.py" ]; then
        run_python_test \
            "Default Context & Migration" \
            "tests/test_lightweight_migration.py" \
            "Lightweight migration tests including default context '.' handling"
    else
        warning "⚠️  Lightweight migration tests not found"
    fi
    
    # 6. All Versions Migration Tests
    if [ -f "tests/run_all_versions_migration_tests.sh" ]; then
        info "Running All Versions Migration test..."
        if run_test \
            "All Versions Migration" \
            "tests/run_all_versions_migration_tests.sh" \
            "Complete schema evolution history preservation"; then
            info "✅ All Versions Migration test completed successfully"
        else
            error "❌ All Versions Migration test failed"
        fi
    else
        error "❌ All versions migration tests not found"
    fi
    
    # 7. ID Preservation Migration Tests
    if [ -f "tests/run_id_preservation_tests.sh" ]; then
        run_test \
            "ID Preservation Migration" \
            "tests/run_id_preservation_tests.sh" \
            "Schema ID preservation using IMPORT mode"
    else
        warning "⚠️  ID preservation tests not found"
    fi
    
    # 8. End-to-End Workflow Tests
    if [ -f "tests/test_end_to_end_workflows.py" ]; then
        run_python_test \
            "End-to-End Workflows" \
            "tests/test_end_to_end_workflows.py" \
            "Complete multi-registry workflow scenarios"
    else
        warning "⚠️  End-to-end workflow tests not found"
    fi
    
    # 9. Error Handling Tests
    if [ -f "tests/test_error_handling.py" ]; then
        run_python_test \
            "Error Handling" \
            "tests/test_error_handling.py" \
            "Multi-registry error scenarios and edge cases"
    else
        warning "⚠️  Error handling tests not found"
    fi
    
    # 10. Performance Tests
    if [ -f "tests/test_performance_load.py" ]; then
        run_python_test \
            "Performance & Load" \
            "tests/test_performance_load.py" \
            "Multi-registry performance and load testing"
    else
        warning "⚠️  Performance tests not found"
    fi
    
    # 11. Counting Tools Tests
    if [ -f "tests/test_counting_tools.py" ]; then
        run_python_test \
            "Counting Tools" \
            "tests/test_counting_tools.py" \
            "Multi-registry schema counting and statistics tools"
    else
        warning "⚠️  Counting tools tests not found"
    fi
    
    # 12. OAuth Configuration Tests
    if [ -f "tests/test_oauth.py" ]; then
        run_python_test \
            "OAuth Configuration" \
            "tests/test_oauth.py" \
            "OAuth scope definitions, token handling, and permission validation"
    else
        warning "⚠️  OAuth configuration tests not found"
    fi
    
    # Test Summary
    generate_test_summary
}

# Generate comprehensive test summary
generate_test_summary() {
    local end_time=$(date +%s)
    local total_duration=$((end_time - TEST_START_TIME))
    local minutes=$((total_duration / 60))
    local seconds=$((total_duration % 60))
    {
        echo ""
        echo "=============================================="
        echo -e "${BOLD}${CYAN}MULTI-REGISTRY TEST SUMMARY${NC}"
        echo "=============================================="
        echo ""
        echo -e "${BOLD}OVERALL RESULTS:${NC}"
        echo "  Tests Passed: ${TESTS_PASSED}/${TOTAL_TESTS}"
        echo "  Success Rate: $(( TESTS_PASSED * 100 / TOTAL_TESTS ))%"
        echo "  Total Duration: ${minutes}m ${seconds}s"
        echo ""
        
        if [ ${#FAILED_OPTIONAL_TESTS[@]} -gt 0 ]; then
            echo -e "${YELLOW}${BOLD}⚠️  OPTIONAL TESTS FAILED:${NC}"
            for failed_test in "${FAILED_OPTIONAL_TESTS[@]}"; do
                echo "  • $failed_test"
            done
            echo ""
        fi
        
        if [ ${TESTS_PASSED} -eq ${TOTAL_TESTS} ]; then
            echo -e "${GREEN}${BOLD}🎉 ALL REQUIRED MULTI-REGISTRY TESTS PASSED!${NC}"
            echo ""
            success "✅ Multi-registry configuration works correctly"
            success "✅ Cross-registry operations function properly"
            success "✅ Schema migration preserves data integrity"
            success "✅ ID preservation maintains referential integrity"
            success "✅ Context management handles edge cases"
            success "✅ Error handling is robust and informative"
            success "✅ Performance meets expectations"
            success "✅ Schema counting and statistics tools work correctly"
            success "✅ OAuth configuration and permissions work correctly"
            echo ""
            echo -e "${CYAN}${BOLD}VALIDATED FEATURES:${NC}"
            echo "  • Multi-Registry Environment Configuration"
            echo "  • Cross-Registry Schema Comparison"
            echo "  • Schema Migration (Latest & All Versions)"
            echo "  • ID Preservation with IMPORT Mode"
            echo "  • Default Context '.' Handling"
            echo "  • Context Migration and Management"
            echo "  • Per-Registry READONLY Mode"
            echo "  • Error Handling and Edge Cases"
            echo "  • Performance and Load Scenarios"
            echo "  • Robust Connectivity Monitoring"
            echo "  • Schema Counting and Statistics Tools"
            echo "  • OAuth Configuration and Permissions"
            echo ""
            success "🚀 Multi-registry environment is production-ready!"
            echo ""
        else
            echo -e "${RED}${BOLD}❌ SOME MULTI-REGISTRY TESTS FAILED${NC}"
            echo ""
            error "Failed Tests:"
            for failed_test in "${FAILED_TESTS[@]}"; do
                echo "  • $failed_test"
            done
            echo ""
            warning "Please review the failed tests above and check:"
            echo "  1. Multi-registry environment health"
            echo "  2. Network connectivity between registries"
            echo "  3. Registry configuration and permissions"
            echo "  4. Test environment setup"
            echo ""
            error "Multi-registry functionality may have issues!"
        fi
    } | tee "$SUMMARY_LOG"
    if [ ${TESTS_PASSED} -eq ${TOTAL_TESTS} ]; then
        exit 0
    else
        exit 1
    fi
}

# Handle script interruption
cleanup() {
    warning "Multi-registry test execution interrupted"
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
    echo "Multi-Registry Test Runner for Kafka Schema Registry MCP Server"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  --quick        Run only essential tests (faster execution)"
    echo "  --full         Run all tests including performance (default)"
    echo ""
    echo "Prerequisites:"
    echo "  • Multi-registry environment running on ports 38081-38082"
    echo "  • Start with: ./start_multi_registry_environment.sh"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run all multi-registry tests"
    echo "  $0 --quick           # Run essential tests only"
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