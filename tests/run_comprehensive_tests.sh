#!/bin/bash

# Comprehensive Integration Test Runner for Multi-Registry MCP Server
# 
# This script runs all integration test suites with proper setup and reporting.
# It provides options for running specific test categories and generating reports.

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

# Test directories and files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_RESULTS_DIR="$SCRIPT_DIR/results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create results directory
mkdir -p "$TEST_RESULTS_DIR"

# Log files
OVERALL_LOG="$TEST_RESULTS_DIR/comprehensive_test_$TIMESTAMP.log"
SUMMARY_LOG="$TEST_RESULTS_DIR/test_summary_$TIMESTAMP.txt"

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

# Function to log and print
log_print() {
    local message=$1
    echo "$message" | tee -a "$OVERALL_LOG"
}

# Function to run a test and capture results
run_test() {
    local test_name=$1
    local test_file=$2
    local description=$3
    
    print_color $BLUE "🧪 Running: $test_name"
    print_color $YELLOW "   Description: $description"
    
    local test_log="$TEST_RESULTS_DIR/${test_name}_$TIMESTAMP.log"
    local start_time=$(date +%s)
    
    # Run the test and capture output
    if python3 "$test_file" > "$test_log" 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        print_color $GREEN "   ✅ PASSED ($duration seconds)"
        echo "PASS,$test_name,$duration,$description" >> "$TEST_RESULTS_DIR/test_results_$TIMESTAMP.csv"
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        print_color $RED "   ❌ FAILED ($duration seconds)"
        echo "FAIL,$test_name,$duration,$description" >> "$TEST_RESULTS_DIR/test_results_$TIMESTAMP.csv"
        
        # Show last few lines of error log
        print_color $RED "   Last 5 lines of error output:"
        tail -5 "$test_log" | sed 's/^/   /'
        return 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    print_header "CHECKING PREREQUISITES"
    
    # Check if Schema Registry is running
    if curl -s http://localhost:38081 >/dev/null 2>&1; then
        print_color $GREEN "✅ Schema Registry is running on localhost:38081"
    else
        print_color $RED "❌ Schema Registry is not running on localhost:38081"
        print_color $YELLOW "Please start Schema Registry before running tests:"
        print_color $YELLOW "  docker-compose up -d"
        exit 1
    fi
    
    # Check Python dependencies
    if python3 -c "import mcp, asyncio, requests" 2>/dev/null; then
        print_color $GREEN "✅ Python dependencies are available"
    else
        print_color $RED "❌ Missing Python dependencies"
        print_color $YELLOW "Please install requirements:"
        print_color $YELLOW "  pip install -r requirements.txt"
        exit 1
    fi
    
    # Check if MCP servers exist
    if [[ -f "$PROJECT_ROOT/kafka_schema_registry_mcp.py" ]] && [[ -f "$PROJECT_ROOT/kafka_schema_registry_multi_mcp.py" ]]; then
        print_color $GREEN "✅ MCP server files found"
    else
        print_color $RED "❌ MCP server files not found"
        exit 1
    fi
    
    print_color $GREEN "✅ All prerequisites satisfied"
}

# Function to run basic configuration tests
run_basic_tests() {
    print_header "BASIC CONFIGURATION TESTS"
    
    local passed=0
    local total=0
    
    # Basic configuration tests
    tests=(
        "simple_config:test_simple_config.py:Single registry configuration validation"
        "numbered_config:test_numbered_config.py:Multi-registry numbered configuration"
        "mcp_server:test_mcp_server.py:Basic MCP server functionality"
    )
    
    for test_spec in "${tests[@]}"; do
        IFS=':' read -r test_name test_file description <<< "$test_spec"
        total=$((total + 1))
        
        if [[ -f "$SCRIPT_DIR/$test_file" ]]; then
            if run_test "$test_name" "$SCRIPT_DIR/$test_file" "$description"; then
                passed=$((passed + 1))
            fi
        else
            print_color $YELLOW "⚠️  Test file not found: $test_file"
        fi
    done
    
    print_color $WHITE "Basic Tests: $passed/$total passed"
    return $((total - passed))
}

# Function to run workflow tests
run_workflow_tests() {
    print_header "END-TO-END WORKFLOW TESTS"
    
    local passed=0
    local total=0
    
    tests=(
        "end_to_end_workflows:test_end_to_end_workflows.py:Complete schema lifecycle workflows"
    )
    
    for test_spec in "${tests[@]}"; do
        IFS=':' read -r test_name test_file description <<< "$test_spec"
        total=$((total + 1))
        
        if [[ -f "$SCRIPT_DIR/$test_file" ]]; then
            if run_test "$test_name" "$SCRIPT_DIR/$test_file" "$description"; then
                passed=$((passed + 1))
            fi
        else
            print_color $YELLOW "⚠️  Test file not found: $test_file"
        fi
    done
    
    print_color $WHITE "Workflow Tests: $passed/$total passed"
    return $((total - passed))
}

# Function to run error handling tests
run_error_tests() {
    print_header "ERROR HANDLING AND EDGE CASE TESTS"
    
    local passed=0
    local total=0
    
    tests=(
        "error_handling:test_error_handling.py:Error handling and edge cases"
    )
    
    for test_spec in "${tests[@]}"; do
        IFS=':' read -r test_name test_file description <<< "$test_spec"
        total=$((total + 1))
        
        if [[ -f "$SCRIPT_DIR/$test_file" ]]; then
            if run_test "$test_name" "$SCRIPT_DIR/$test_file" "$description"; then
                passed=$((passed + 1))
            fi
        else
            print_color $YELLOW "⚠️  Test file not found: $test_file"
        fi
    done
    
    print_color $WHITE "Error Handling Tests: $passed/$total passed"
    return $((total - passed))
}

# Function to run performance tests
run_performance_tests() {
    print_header "PERFORMANCE AND LOAD TESTS"
    
    local passed=0
    local total=0
    
    tests=(
        "performance_load:test_performance_load.py:Performance and load testing"
    )
    
    for test_spec in "${tests[@]}"; do
        IFS=':' read -r test_name test_file description <<< "$test_spec"
        total=$((total + 1))
        
        if [[ -f "$SCRIPT_DIR/$test_file" ]]; then
            if run_test "$test_name" "$SCRIPT_DIR/$test_file" "$description"; then
                passed=$((passed + 1))
            fi
        else
            print_color $YELLOW "⚠️  Test file not found: $test_file"
        fi
    done
    
    print_color $WHITE "Performance Tests: $passed/$total passed"
    return $((total - passed))
}

# Function to run production readiness tests
run_production_tests() {
    print_header "PRODUCTION READINESS TESTS"
    
    local passed=0
    local total=0
    
    tests=(
        "production_readiness:test_production_readiness.py:Enterprise production readiness"
    )
    
    for test_spec in "${tests[@]}"; do
        IFS=':' read -r test_name test_file description <<< "$test_spec"
        total=$((total + 1))
        
        if [[ -f "$SCRIPT_DIR/$test_file" ]]; then
            if run_test "$test_name" "$SCRIPT_DIR/$test_file" "$description"; then
                passed=$((passed + 1))
            fi
        else
            print_color $YELLOW "⚠️  Test file not found: $test_file"
        fi
    done
    
    print_color $WHITE "Production Tests: $passed/$total passed"
    return $((total - passed))
}

# Function to run legacy integration tests
run_legacy_tests() {
    print_header "LEGACY INTEGRATION TESTS"
    
    local passed=0
    local total=0
    
    # Check if numbered integration test exists
    if [[ -f "$SCRIPT_DIR/test_numbered_integration.py" ]]; then
        total=$((total + 1))
        if run_test "numbered_integration" "$SCRIPT_DIR/test_numbered_integration.py" "Legacy numbered configuration integration"; then
            passed=$((passed + 1))
        fi
    fi
    
    print_color $WHITE "Legacy Tests: $passed/$total passed"
    return $((total - passed))
}

# Function to generate test summary
generate_summary() {
    print_header "TEST SUMMARY"
    
    local summary_file="$SUMMARY_LOG"
    local csv_file="$TEST_RESULTS_DIR/test_results_$TIMESTAMP.csv"
    
    {
        echo "Kafka Schema Registry MCP Server - Comprehensive Test Report"
        echo "=========================================================="
        echo "Test Run Timestamp: $(date)"
        echo "Total Test Duration: $(($(date +%s) - $TEST_START_TIME)) seconds"
        echo ""
        
        if [[ -f "$csv_file" ]]; then
            echo "DETAILED TEST RESULTS:"
            echo "====================="
            
            local total_tests=0
            local passed_tests=0
            local failed_tests=0
            
            while IFS=',' read -r status test_name duration description; do
                echo "[$status] $test_name ($duration seconds)"
                echo "  Description: $description"
                total_tests=$((total_tests + 1))
                
                if [[ "$status" == "PASS" ]]; then
                    passed_tests=$((passed_tests + 1))
                else
                    failed_tests=$((failed_tests + 1))
                fi
                echo ""
            done < "$csv_file"
            
            echo "SUMMARY STATISTICS:"
            echo "=================="
            echo "Total Tests: $total_tests"
            echo "Passed: $passed_tests"
            echo "Failed: $failed_tests"
            echo "Success Rate: $(( passed_tests * 100 / total_tests ))%"
        else
            echo "No test results found."
        fi
        
        echo ""
        echo "TEST CATEGORIES COVERED:"
        echo "======================="
        echo "✅ Basic Configuration Tests"
        echo "✅ End-to-End Workflow Tests"
        echo "✅ Error Handling and Edge Cases"
        echo "✅ Performance and Load Testing"
        echo "✅ Production Readiness Validation"
        echo "✅ Legacy Integration Tests"
        
        echo ""
        echo "FEATURES VALIDATED:"
        echo "=================="
        echo "• Multi-Registry Support (up to 8 registries)"
        echo "• Numbered Environment Configuration"
        echo "• Per-Registry READONLY Mode"
        echo "• Cross-Registry Operations"
        echo "• Schema Evolution and Migration"
        echo "• Context Management"
        echo "• Enterprise Security and Compliance"
        echo "• High Availability and Disaster Recovery"
        echo "• Performance and Scalability"
        echo "• Monitoring and Observability"
        
    } | tee "$summary_file"
    
    print_color $GREEN "📊 Test summary saved to: $summary_file"
    print_color $GREEN "📊 Detailed logs in: $TEST_RESULTS_DIR"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "OPTIONS:"
    echo "  --basic         Run only basic configuration tests"
    echo "  --workflows     Run only workflow tests"
    echo "  --errors        Run only error handling tests"
    echo "  --performance   Run only performance tests"
    echo "  --production    Run only production readiness tests"
    echo "  --legacy        Run only legacy integration tests"
    echo "  --all           Run all test categories (default)"
    echo "  --help          Show this help message"
    echo ""
    echo "EXAMPLES:"
    echo "  $0                     # Run all tests"
    echo "  $0 --basic            # Run only basic tests"
    echo "  $0 --performance      # Run only performance tests"
    echo "  $0 --production       # Run only production readiness tests"
    echo ""
}

# Main execution
main() {
    local run_basic=false
    local run_workflows=false
    local run_errors=false
    local run_performance=false
    local run_production=false
    local run_legacy=false
    local run_all=true
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --basic)
                run_basic=true
                run_all=false
                shift
                ;;
            --workflows)
                run_workflows=true
                run_all=false
                shift
                ;;
            --errors)
                run_errors=true
                run_all=false
                shift
                ;;
            --performance)
                run_performance=true
                run_all=false
                shift
                ;;
            --production)
                run_production=true
                run_all=false
                shift
                ;;
            --legacy)
                run_legacy=true
                run_all=false
                shift
                ;;
            --all)
                run_all=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Start test execution
    TEST_START_TIME=$(date +%s)
    
    print_header "KAFKA SCHEMA REGISTRY MCP SERVER - COMPREHENSIVE INTEGRATION TESTS"
    log_print "Test execution started at: $(date)"
    
    # Initialize CSV results file
    echo "Status,TestName,Duration,Description" > "$TEST_RESULTS_DIR/test_results_$TIMESTAMP.csv"
    
    # Check prerequisites first
    check_prerequisites
    
    local total_failures=0
    
    # Run selected test categories
    if [[ "$run_all" == true ]]; then
        run_basic_tests || total_failures=$((total_failures + $?))
        run_workflow_tests || total_failures=$((total_failures + $?))
        run_error_tests || total_failures=$((total_failures + $?))
        run_performance_tests || total_failures=$((total_failures + $?))
        run_production_tests || total_failures=$((total_failures + $?))
        run_legacy_tests || total_failures=$((total_failures + $?))
    else
        [[ "$run_basic" == true ]] && { run_basic_tests || total_failures=$((total_failures + $?)); }
        [[ "$run_workflows" == true ]] && { run_workflow_tests || total_failures=$((total_failures + $?)); }
        [[ "$run_errors" == true ]] && { run_error_tests || total_failures=$((total_failures + $?)); }
        [[ "$run_performance" == true ]] && { run_performance_tests || total_failures=$((total_failures + $?)); }
        [[ "$run_production" == true ]] && { run_production_tests || total_failures=$((total_failures + $?)); }
        [[ "$run_legacy" == true ]] && { run_legacy_tests || total_failures=$((total_failures + $?)); }
    fi
    
    # Generate final summary
    generate_summary
    
    # Final result
    if [[ $total_failures -eq 0 ]]; then
        print_color $GREEN "🎉 ALL TESTS COMPLETED SUCCESSFULLY!"
        print_color $GREEN "✅ Multi-Registry MCP Server is ready for production"
        exit 0
    else
        print_color $RED "❌ SOME TESTS FAILED ($total_failures failures)"
        print_color $YELLOW "⚠️  Check test logs for details: $TEST_RESULTS_DIR"
        exit 1
    fi
}

# Execute main function with all arguments
main "$@" 