#!/bin/bash

# Unified Test Runner for Kafka Schema Registry MCP Server
# 
# This script provides a complete test execution pipeline:
# 1. Starts unified test environment (multi-registry mode)
# 2. Runs comprehensive test suite (both single and multi-registry modes)
# 3. Collects and reports results
# 4. Cleans up environment
#
# NEW in v2.0.0: OAuth 2.1 Generic Discovery Tests
# - Tests OAuth 2.1 generic discovery instead of provider-specific configurations
# - Validates RFC 8414 compliance and automatic endpoint discovery
# - Tests universal OAuth 2.1 compatibility with any compliant provider
#
# NEW: SLIM_MODE Integration Tests
# - Tests SLIM_MODE functionality that reduces tools from 53+ to ~15
# - Validates performance improvements and tool reduction
#
# NEW in v2.1.0: Smart Defaults Tests
# - Tests pattern recognition and learning engine
# - Validates elicitation integration with smart suggestions
# - Tests configuration and privacy controls
#
# Usage: ./run_all_tests.sh [options]
# Options:
#   --quick     Run only essential tests (faster execution)
#   --no-cleanup Skip environment cleanup at the end
#   --help      Show help message

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_RESULTS_DIR="$SCRIPT_DIR/results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
CLEANUP_ENVIRONMENT=true
QUICK_MODE=false

# Log files
UNIFIED_LOG="$TEST_RESULTS_DIR/unified_test_$TIMESTAMP.log"
FINAL_SUMMARY="$TEST_RESULTS_DIR/final_summary_$TIMESTAMP.txt"

# Create results directory
mkdir -p "$TEST_RESULTS_DIR"

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
    print_color $CYAN "$(printf '=%.0s' {1..80})"
    print_color $WHITE "  $title"
    print_color $CYAN "$(printf '=%.0s' {1..80})"
    echo
}

# Function to log and print
log_print() {
    local message=$1
    echo "$message" | tee -a "$UNIFIED_LOG"
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --quick)
                QUICK_MODE=true
                shift
                ;;
            --no-cleanup)
                CLEANUP_ENVIRONMENT=false
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                print_color $RED "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Show help message
show_help() {
    print_color $WHITE "Unified Test Runner for Kafka Schema Registry MCP Server"
    echo
    print_color $CYAN "USAGE:"
    print_color $WHITE "  ./run_all_tests.sh [options]"
    echo
    print_color $CYAN "OPTIONS:"
    print_color $WHITE "  --quick       Run only essential tests (faster execution)"
    print_color $WHITE "  --no-cleanup  Skip environment cleanup at the end"
    print_color $WHITE "  --help        Show this help message"
    echo
    print_color $CYAN "EXAMPLES:"
    print_color $WHITE "  ./run_all_tests.sh                    # Full test suite"
    print_color $WHITE "  ./run_all_tests.sh --quick            # Essential tests only"
    print_color $WHITE "  ./run_all_tests.sh --no-cleanup       # Keep environment running"
    echo
    print_color $CYAN "DESCRIPTION:"
    print_color $WHITE "  This script provides a complete test execution pipeline:"
    print_color $WHITE "  1. Starts unified test environment (multi-registry mode)"
    print_color $WHITE "  2. Runs comprehensive test suite (single + multi-registry modes)"
    print_color $WHITE "  3. Collects and reports results"
    print_color $WHITE "  4. Cleans up environment (unless --no-cleanup)"
    echo
}

# Check prerequisites
check_prerequisites() {
    print_header "CHECKING PREREQUISITES"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_color $RED "❌ Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_color $RED "❌ Docker is not running"
        exit 1
    fi
    
    print_color $GREEN "✅ Docker is available and running"
    
    # Check Python dependencies
    if python3 -c "import mcp, asyncio, requests" 2>/dev/null; then
        print_color $GREEN "✅ Python dependencies are available"
    else
        print_color $RED "❌ Missing Python dependencies"
        print_color $YELLOW "Please install requirements: pip install -r ../requirements.txt"
        exit 1
    fi
    
    # Check unified server file
    if [[ -f "$PROJECT_ROOT/kafka_schema_registry_unified_mcp.py" ]]; then
        print_color $GREEN "✅ Unified MCP server file found"
    else
        print_color $RED "❌ Unified MCP server file not found"
        exit 1
    fi
    
    # Check MCP compliance test files
    if [[ -f "$SCRIPT_DIR/test_mcp_compliance.py" ]]; then
        print_color $GREEN "✅ MCP compliance test file found (tests directory)"
    else
        print_color $YELLOW "⚠️  MCP compliance test file not found in tests directory"
    fi
    
    if [[ -f "$SCRIPT_DIR/test_mcp_header_validation.py" ]]; then
        print_color $GREEN "✅ MCP header validation test file found (tests directory)"
    else
        print_color $YELLOW "⚠️  MCP header validation test file not found in tests directory"
    fi
    
    if [[ -f "$SCRIPT_DIR/test_structured_output.py" ]]; then
        print_color $GREEN "✅ MCP structured output test file found (tests directory)"
    else
        print_color $YELLOW "⚠️  MCP structured output test file not found in tests directory"
    fi
    
    # Check SLIM_MODE test file
    if [[ -f "$SCRIPT_DIR/test_slim_mode_integration.py" ]]; then
        print_color $GREEN "✅ SLIM_MODE integration test file found"
    else
        print_color $YELLOW "⚠️  SLIM_MODE integration test file not found"
    fi

    # Check smart defaults test files
    if [[ -f "$SCRIPT_DIR/test_smart_defaults.py" ]]; then
        print_color $GREEN "✅ Smart defaults test file found"
    else
        print_color $YELLOW "⚠️  Smart defaults test file not found"
    fi
    
    print_color $GREEN "✅ All prerequisites satisfied"
}

# Start test environment
start_environment() {
    print_header "STARTING UNIFIED TEST ENVIRONMENT"
    
    log_print "$(date): Starting unified test environment..."
    
    # Stop any existing environment first
    print_color $BLUE "🧹 Cleaning up any existing environment..."
    if [[ -f "$SCRIPT_DIR/stop_test_environment.sh" ]]; then
        "$SCRIPT_DIR/stop_test_environment.sh" clean > /dev/null 2>&1 || true
    fi
    
    # Wait a moment for cleanup
    sleep 3
    
    # Start the unified environment in full multi-registry mode
    print_color $BLUE "🚀 Starting unified test environment..."
    if [[ -f "$SCRIPT_DIR/start_test_environment.sh" ]]; then
        if "$SCRIPT_DIR/start_test_environment.sh" multi; then
            print_color $GREEN "✅ Unified test environment started successfully"
            log_print "$(date): Environment started successfully"
        else
            print_color $RED "❌ Failed to start unified test environment"
            log_print "$(date): Environment startup failed"
            exit 1
        fi
    else
        print_color $RED "❌ start_test_environment.sh not found"
        exit 1
    fi
    
    # Additional health check
    print_color $BLUE "🔍 Verifying environment health..."
    sleep 5
    
    # Check registry connectivity
    local dev_healthy=false
    local prod_healthy=false
    
    if curl -s http://localhost:38081/subjects &> /dev/null; then
        print_color $GREEN "✅ DEV Registry (38081) is responding"
        dev_healthy=true
    else
        print_color $RED "❌ DEV Registry (38081) is not responding"
    fi
    
    if curl -s http://localhost:38082/subjects &> /dev/null; then
        print_color $GREEN "✅ PROD Registry (38082) is responding"
        prod_healthy=true
    else
        print_color $RED "❌ PROD Registry (38082) is not responding"
    fi
    
    if [[ "$dev_healthy" == false ]] || [[ "$prod_healthy" == false ]]; then
        print_color $RED "❌ Environment is not fully healthy"
        print_color $YELLOW "Check logs with: docker-compose logs"
        exit 1
    fi
    
    print_color $GREEN "🎉 Environment is ready for testing!"
}

# Run test suite
run_tests() {
    print_header "RUNNING COMPREHENSIVE TEST SUITE"
    
    local test_start_time=$(date +%s)
    
    log_print "$(date): Starting test execution..."
    
    if [[ "$QUICK_MODE" == true ]]; then
        print_color $YELLOW "🏃 Running in QUICK mode - essential tests only"
    else
        print_color $BLUE "🔬 Running FULL test suite - all tests"
    fi
    
    # Test categories to run
    declare -a test_categories
    
    if [[ "$QUICK_MODE" == true ]]; then
        test_categories=(
            "basic_unified_server"
            "essential_integration"
            "multi_registry_core"
            "mcp_container_tests"
            "mcp_compliance_tests"
            "slim_mode_tests"
            "smart_defaults_tests"
        )
    else
        test_categories=(
            "basic_unified_server"
            "integration_tests"
            "multi_registry_tests"
            "mcp_container_tests"
            "mcp_compliance_tests"
            "slim_mode_tests"
            "advanced_features"
            "smart_defaults_tests"
        )
    fi
    
    # Run each test category
    for category in "${test_categories[@]}"; do
        run_test_category "$category" || true
    done
    
    local test_end_time=$(date +%s)
    local test_duration=$((test_end_time - test_start_time))
    
    print_header "TEST EXECUTION SUMMARY"
    print_color $WHITE "Test Duration: ${test_duration} seconds"
    print_color $WHITE "Environment: Unified Multi-registry (DEV + PROD)"
    print_color $WHITE "Mode: $([ "$QUICK_MODE" == true ] && echo "QUICK" || echo "FULL")"
    
    log_print "$(date): Test execution completed in ${test_duration} seconds"
}

# Run specific test category
run_test_category() {
    local category=$1
    print_color $BLUE "📂 Running category: $category"
    
    case $category in
        "basic_unified_server")
            run_basic_tests
            ;;
        "essential_integration")
            run_essential_integration_tests
            ;;
        "integration_tests")
            run_integration_tests
            ;;
        "multi_registry_core")
            run_multi_registry_core_tests
            ;;
        "multi_registry_tests")
            run_multi_registry_tests
            ;;
        "mcp_compliance_tests")
            run_mcp_compliance_tests
            ;;
        "slim_mode_tests")
            run_slim_mode_tests
            ;;
        "advanced_features")
            run_advanced_feature_tests
            ;;
        "mcp_container_tests")
            run_mcp_container_tests
            ;;
        "smart_defaults_tests")
            run_smart_defaults_tests
            ;;
        *)
            print_color $YELLOW "⚠️  Unknown test category: $category"
            ;;
    esac
}

# Run basic unified server tests
run_basic_tests() {
    print_color $CYAN "🔧 Basic Unified Server Tests"
    
    local tests=(
        "test_basic_server.py:Basic server import and functionality"
        "test_mcp_server.py:MCP protocol connectivity"
        "test_prompts.py:MCP prompts functionality and content validation"
        "test_config.py:Configuration management"
        "test_user_roles.py:OAuth user role assignment and scope extraction"
        "test_remote_mcp_server.py:Remote MCP server deployment functionality"
        "test_remote_mcp_metrics.py:Remote MCP server metrics and monitoring"
        "test_simple_python.py:Python environment validation"
        "test_ssrf_vulnerability.py:SSRF vulnerability protection and URL validation"
    )
    
    run_test_list "${tests[@]}"
}

# Run essential integration tests (for quick mode)
run_essential_integration_tests() {
    print_color $CYAN "⚡ Essential Integration Tests"
    
    local tests=(
        "test_integration.py:Core schema operations"
        "test_prompts.py:MCP prompts functionality and workflow scenarios"
        "test_viewonly_mode.py:VIEWONLY mode enforcement"
        "test_counting_tools.py:Schema counting and statistics"
        "test_statistics_tasks.py:Statistics tasks with async optimization"
        "test_ssl_tls_integration.py:SSL/TLS security enhancement integration (issue #24)"
        "test_oauth.py:OAuth 2.1 generic discovery and authentication"
        "test_github_oauth.py:GitHub OAuth 2.1 integration with fallback handling"
        "test_oauth_discovery.py:OAuth 2.1 discovery endpoints and RFC 8414 compliance"
        "test_user_roles.py:OAuth user role assignment and scope extraction"
        "test_remote_mcp_server.py:Remote MCP server deployment functionality"
        "test_remote_mcp_metrics.py:Remote MCP server metrics and monitoring"
        "test_elicitation.py:Elicitation framework core functionality"
        "test_multi_step_elicitation.py:Multi-step elicitation workflows (Issue #73 - essential functionality)"
    )
    
    run_test_list "${tests[@]}"
}

# Run full integration tests
run_integration_tests() {
    print_color $CYAN "🔗 Integration Tests"
    
    local tests=(
        "test_viewonly_mcp_client.py:VIEWONLY mode with MCP client"
        "test_viewonly_validation.py:VIEWONLY mode validation"
        "test_docker_mcp.py:Docker integration"
        "advanced_mcp_test.py:Advanced MCP functionality"
        "test_elicitation_integration.py:Elicitation integration with MCP tools"
        "test_elicitation_edge_cases.py:Elicitation edge case handling"
    )
    
    run_test_list "${tests[@]}"
}

# Run multi-registry core tests (for quick mode)
run_multi_registry_core_tests() {
    print_color $CYAN "🏢 Multi-Registry Core Tests"
    
    local tests=(
        "test_multi_registry_mcp.py:Multi-registry server functionality"
        "test_multi_registry_validation.py:Multi-registry configuration validation"
        "test_numbered_integration.py:Numbered environment configuration"
    )
    
    run_test_list "${tests[@]}"
}

# Run full multi-registry tests
run_multi_registry_tests() {
    print_color $CYAN "🏢 Multi-Registry Tests"
    
    local tests=(
        "test_multi_registry_mcp.py:Multi-registry server functionality"
        "test_multi_registry_validation.py:Multi-registry configuration validation"
        "test_numbered_integration.py:Numbered environment configuration"
        "test_default_context_dot_simple.py:Default context handling"
        "test_batch_cleanup.py:Batch cleanup operations"
    )
    
    run_test_list "${tests[@]}"
}

# Run MCP compliance tests (UPDATED CATEGORY)
run_mcp_compliance_tests() {
    print_color $CYAN "🛡️  MCP 2025-06-18 Compliance Tests"
    
    # All MCP compliance tests are now in the tests directory
    local tests=(
        "test_mcp_compliance.py:MCP-Protocol-Version header validation and compliance verification"
        "test_mcp_header_validation.py:MCP header validation middleware and exempt path functionality"
        "test_structured_output.py:Structured output schema validation and MCP tool response compliance"
        "test_mcp_ping.py:MCP ping/pong protocol support and server health checking"
        "test_registry_specific_resources.py:Registry-specific resources (registry://status/{name}, registry://info/{name}, registry://mode/{name}, registry://names, schema://{name}/{context}/{subject}, schema://{name}/{subject})"
    )
    
    run_test_list "${tests[@]}"
}

# Run SLIM_MODE tests (NEW CATEGORY)
run_slim_mode_tests() {
    print_color $CYAN "🏃 SLIM_MODE Integration Tests"
    
    local tests=(
        "test_slim_mode_integration.py:SLIM_MODE functionality - tool reduction from 53+ to ~15 for improved LLM performance"
    )
    
    run_test_list "${tests[@]}"
}

# Run MCP container tests
run_mcp_container_tests() {
    print_color $CYAN "🐳 MCP Container Integration Tests"
    
    # Check if MCP server container is healthy
    print_color $BLUE "   🔍 Checking MCP server container health..."
    if docker ps --filter "name=mcp-server" --format "{{.Names}}" | grep -q "mcp-server"; then
        local health_status=$(docker inspect --format='{{.State.Health.Status}}' mcp-server 2>/dev/null || echo "unknown")
        if [[ "$health_status" == "healthy" ]]; then
            print_color $GREEN "   ✅ MCP server container is healthy"
        else
            print_color $YELLOW "   ⚠️  MCP server container health: $health_status"
        fi
    else
        print_color $YELLOW "   ⚠️  MCP server container not found, tests may fail"
    fi
    
    local tests=(
        "test_mcp_container_integration.py:MCP server container integration and protocol testing"
    )
    
    run_test_list "${tests[@]}"
}

# Run smart defaults tests
run_smart_defaults_tests() {
    print_color $CYAN "🧠 Smart Defaults Tests"
    
    local tests=(
        "test_smart_defaults.py:Smart defaults pattern recognition and learning engine"
    )
    
    run_test_list "${tests[@]}"
}

# Run advanced feature tests (comparison, migration, complex workflows)
run_advanced_feature_tests() {
    print_color $CYAN "🚀 Advanced Feature Tests (Comparison & Migration)"
    
    local tests=(
        "test_migration_integration.py:Schema migration functionality"
        "test_migration_implementation.py:Migration implementation details"
        "test_lightweight_migration.py:Lightweight migration operations"
        "test_lightweight_migration_integration.py:Lightweight migration integration"
        "test_migrate_context_docker_config.py:Docker migration command generation"
        "test_all_versions_migration.py:All versions migration testing"
        "test_version_migration.py:Version-specific migration testing"
        "test_sparse_version_migration.py:Sparse version migration"
        "test_id_preservation_migration.py:ID preservation migration"
        "test_bulk_migration.py:Bulk migration operations"
        "test_bulk_operations_wizard.py:Bulk Operations Wizard with elicitation-based workflows"
        "test_compatibility_migration.py:Compatibility migration testing"
        "test_batch_cleanup_integration.py:Advanced batch cleanup"
        "test_registry_comparison.py:Registry comparison functionality"
        "test_schema_drift.py:Schema drift detection and handling"
        "test_end_to_end_workflows.py:End-to-end workflow testing"
        "test_error_handling.py:Error handling and recovery"
        "test_all_tools_validation.py:All MCP tools validation"
        "test_metadata_integration.py:Consolidated metadata integration testing"
        "test_performance_load.py:Performance and load testing"
        "test_production_readiness.py:Production readiness validation"
        "test_resource_linking.py:Resource linking and URI navigation (MCP 2025-06-18 compliance)"
        "test_schema_evolution_assistant.py:Schema Evolution Assistant with breaking change detection and migration strategies"
    )
    
    run_test_list "${tests[@]}"
}

# Run a list of tests
run_test_list() {
    local tests=("$@")
    
    for test_spec in "${tests[@]}"; do
        IFS=':' read -r test_file description <<< "$test_spec"
        
        if [[ -f "$SCRIPT_DIR/$test_file" ]]; then
            print_color $BLUE "   🧪 Running: $description"
            local test_start=$(date +%s)
            
            if python3 "$SCRIPT_DIR/$test_file" </dev/null > "$TEST_RESULTS_DIR/${test_file%.py}_$TIMESTAMP.log" 2>&1; then
                local test_end=$(date +%s)
                local duration=$((test_end - test_start))
                print_color $GREEN "   ✅ PASSED ($duration seconds)"
                log_print "PASS,$test_file,$duration,$description"
            else
                local test_end=$(date +%s)
                local duration=$((test_end - test_start))
                print_color $RED "   ❌ FAILED ($duration seconds)"
                log_print "FAIL,$test_file,$duration,$description"
                
                # Show last few lines of error
                print_color $RED "   Last 3 lines of error:"
                tail -3 "$TEST_RESULTS_DIR/${test_file%.py}_$TIMESTAMP.log" 2>/dev/null | sed 's/^/   /' || true
            fi
        else
            print_color $YELLOW "   ⚠️  Test file not found: $test_file"
        fi
    done
}

# Generate final summary
generate_summary() {
    print_header "GENERATING FINAL SUMMARY"
    
    local end_time=$(date)
    local total_duration=$(($(date +%s) - START_TIME))
    
    # Count results
    local total_tests=0
    local passed_tests=0
    local failed_tests=0
    
    if [[ -f "$UNIFIED_LOG" ]]; then
        total_tests=$(grep -c "^PASS\|^FAIL" "$UNIFIED_LOG" 2>/dev/null || echo 0)
        passed_tests=$(grep -c "^PASS" "$UNIFIED_LOG" 2>/dev/null || echo 0)
        failed_tests=$(grep -c "^FAIL" "$UNIFIED_LOG" 2>/dev/null || echo 0)
        # Clean up any newlines or spaces
        total_tests=$(echo "$total_tests" | tr -d '\n ')
        passed_tests=$(echo "$passed_tests" | tr -d '\n ')
        failed_tests=$(echo "$failed_tests" | tr -d '\n ')
    fi
    
    # Calculate success rate
    local success_rate=0
    if [[ $total_tests -gt 0 ]]; then
        success_rate=$(echo "scale=1; $passed_tests * 100 / $total_tests" | bc 2>/dev/null || echo "0")
    fi
    
    # Generate summary report
    cat > "$FINAL_SUMMARY" << EOF
Kafka Schema Registry MCP Server - Unified Test Results
======================================================

Execution Details:
- Start Time: $START_TIME_STR
- End Time: $end_time
- Total Duration: ${total_duration} seconds
- Test Mode: $([ "$QUICK_MODE" == true ] && echo "QUICK" || echo "FULL")
- Environment: Unified Multi-registry (DEV + PROD)

Test Results:
- Total Tests: $total_tests
- Passed: $passed_tests
- Failed: $failed_tests
- Success Rate: ${success_rate}%

Environment Status:
- DEV Registry: http://localhost:38081
- PROD Registry: http://localhost:38082
- Docker Containers: $(docker ps --format "table {{.Names}}" | grep -E "(kafka|schema-registry)" | wc -l 2>/dev/null || echo 0) running

Test Categories Executed:
$([ "$QUICK_MODE" == true ] && echo "- Basic Unified Server Tests
- Essential Integration Tests  
- Multi-Registry Core Tests
- MCP Container Integration Tests
- MCP 2025-06-18 Compliance Tests ⭐
- SLIM_MODE Integration Tests 🏃" || echo "- Basic Unified Server Tests (imports, connectivity)
- Integration Tests (schema operations, viewonly mode)
- Multi-Registry Tests (multi-registry operations)
- MCP Container Integration Tests (Docker container deployment)
- MCP 2025-06-18 Compliance Tests (header validation, protocol compliance) ⭐
- Advanced Feature Tests (comparison, migration, workflows, resource linking)
- Smart Defaults Tests (pattern recognition, learning engine) 🧠")

Log Files:
- Unified Log: $UNIFIED_LOG
- Individual Test Logs: $TEST_RESULTS_DIR/*_$TIMESTAMP.log

$(if [[ $failed_tests -gt 0 ]]; then
echo ""
echo "Failed Tests:"
grep "^FAIL" "$UNIFIED_LOG" 2>/dev/null | cut -d',' -f2 | sed 's/^/- /' || echo "None"
else
echo ""
echo "🎉 All tests passed successfully!"
fi)

⭐ NEW: MCP 2025-06-18 Compliance Tests validate header validation middleware,
   exempt path functionality, and protocol version compliance.

🏃 NEW: SLIM_MODE Integration Tests validate tool reduction from 53+ to ~15 for
   improved LLM performance and reduced token usage.

🔗 Resource Linking Tests: URI navigation and link generation for enhanced MCP client experience.

🚀 OAuth 2.1 Generic Discovery: Tests now validate universal OAuth 2.1 compatibility
   instead of provider-specific configurations (75% configuration reduction).

🧠 Smart Defaults Tests: Pattern recognition and learning engine for intelligent
   form pre-population based on user behavior and organizational conventions.

📁 Test Organization: All MCP compliance tests are now properly organized in the tests directory
   for better maintainability and CI/CD integration.

EOF
    
    # Display summary
    cat "$FINAL_SUMMARY"
    
    print_color $GREEN "📊 Summary saved to: $FINAL_SUMMARY"
    
    # Log final status
    if [[ $failed_tests -eq 0 ]]; then
        log_print "$(date): All tests completed successfully"
        print_color $GREEN "🎉 ALL TESTS PASSED!"
    else
        log_print "$(date): $failed_tests tests failed"
        print_color $RED "❌ $failed_tests TESTS FAILED"
    fi
}

# Cleanup environment
cleanup_environment() {
    if [[ "$CLEANUP_ENVIRONMENT" == true ]]; then
        print_header "CLEANING UP ENVIRONMENT"
        
        print_color $BLUE "🧹 Stopping unified test environment..."
        
        if [[ -f "$SCRIPT_DIR/stop_test_environment.sh" ]]; then
            if "$SCRIPT_DIR/stop_test_environment.sh" clean > /dev/null 2>&1; then
                print_color $GREEN "✅ Environment cleanup completed"
                log_print "$(date): Environment cleanup successful"
            else
                print_color $YELLOW "⚠️  Environment cleanup encountered issues"
                log_print "$(date): Environment cleanup had issues"
            fi
        else
            print_color $YELLOW "⚠️  stop_test_environment.sh not found"
        fi
    else
        print_header "SKIPPING CLEANUP"
        print_color $YELLOW "⚠️  Environment cleanup skipped (--no-cleanup flag)"
        print_color $BLUE "To cleanup manually, run:"
        print_color $WHITE "  ./stop_test_environment.sh"
        log_print "$(date): Environment cleanup skipped by user request"
    fi
}

# Main execution
main() {
    # Record start time
    START_TIME=$(date +%s)
    START_TIME_STR=$(date)
    
    print_header "KAFKA SCHEMA REGISTRY MCP SERVER - UNIFIED TEST RUNNER"
    
    log_print "$(date): Starting unified test execution"
    log_print "Arguments: $*"
    
    # Parse command line arguments
    parse_args "$@"
    
    # Set up error handling
    trap cleanup_environment EXIT
    
    # Execute test pipeline
    check_prerequisites
    start_environment
    run_tests
    generate_summary
    
    # Determine exit code
    local failed_tests=0
    if [[ -f "$UNIFIED_LOG" ]]; then
        failed_tests=$(grep -c "^FAIL" "$UNIFIED_LOG" 2>/dev/null || echo 0)
        failed_tests=$(echo "$failed_tests" | tr -d '\n ')
    fi
    
    if [[ $failed_tests -eq 0 ]]; then
        print_color $GREEN "🎉 Unified test execution completed successfully!"
        exit 0
    else
        print_color $RED "❌ Unified test execution completed with $failed_tests failures"
        exit 1
    fi
}

# Execute main function with all arguments
main "$@"
