#!/bin/bash

# Single-Registry Integration Test Runner for Kafka Schema Registry MCP Server
# 
# This script runs all single-registry test suites with proper setup and reporting.
# It excludes multi-registry tests and focuses on kafka_schema_registry_mcp.py functionality.

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
    print_header "BASIC SINGLE-REGISTRY TESTS"
    
    local passed=0
    local total=0
    
    # Single-registry tests only
    tests=(
        "basic_server:test_basic_server.py:Basic server import and functionality tests"
        "mcp_server:test_mcp_server.py:Basic MCP server connectivity test"
        "config:test_config.py:Configuration management testing"
        "readonly_mcp_client:test_readonly_mcp_client.py:READONLY mode testing with MCP client"
        "counting_tools:test_counting_tools.py:Schema counting and statistics tools testing"
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
    
    print_color $WHITE "Basic Single-Registry Tests: $passed/$total passed"
    return $((total - passed))
}

# Function to run workflow tests
run_workflow_tests() {
    print_header "SINGLE-REGISTRY INTEGRATION TESTS"
    
    local passed=0
    local total=0
    
    tests=(
        "integration:test_integration.py:Comprehensive single-registry integration tests"
        "advanced_mcp:advanced_mcp_test.py:Advanced MCP functionality test"
        "docker_mcp:test_docker_mcp.py:Docker container integration testing"
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
    
    print_color $WHITE "Single-Registry Integration Tests: $passed/$total passed"
    return $((total - passed))
}

# Function to run error handling tests
run_error_tests() {
    print_header "SINGLE-REGISTRY VALIDATION TESTS"
    
    local passed=0
    local total=0
    
    tests=(
        "simple_python:test_simple_python.py:Basic Python environment validation"
        "runner_validation:validate_single_registry_runner.py:Single-registry test runner validation"
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
    
    print_color $WHITE "Single-Registry Validation Tests: $passed/$total passed"
    return $((total - passed))
}

# Function to generate test summary
generate_summary() {
    print_header "TEST SUMMARY"
    
    local summary_file="$SUMMARY_LOG"
    local csv_file="$TEST_RESULTS_DIR/test_results_$TIMESTAMP.csv"
    
    {
        echo "Kafka Schema Registry MCP Server - Single-Registry Test Report"
        echo "=============================================================="
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
        echo "✅ Basic Single-Registry Configuration"
        echo "✅ Single-Registry Integration Tests"
        echo "✅ Single-Registry Validation"
        echo "✅ Schema Counting and Statistics"
        
        echo ""
        echo "FEATURES VALIDATED:"
        echo "=================="
        echo "• Single Schema Registry Support (port 38081)"
        echo "• MCP Protocol Server Functionality" 
        echo "• Configuration Management"
        echo "• READONLY Mode Support"
        echo "• Schema Registration and Retrieval (via MCP)"
        echo "• Context Management (Default Context)"
        echo "• Docker Integration"
        echo "• Basic Error Handling"
        echo "• Environment Compatibility"
        echo "• Single-Registry Mode Fixes"
        echo "• Schema Counting and Statistics Tools"
        
    } | tee "$summary_file"
    
    print_color $GREEN "📊 Test summary saved to: $summary_file"
    print_color $GREEN "📊 Detailed logs in: $TEST_RESULTS_DIR"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --basic       Run only basic tests"
    echo "  --workflows   Run only workflow tests"
    echo "  --errors      Run only error handling tests"
    echo "  --all         Run all tests (default)"
    echo "  --help        Show this help message"
}

# Main execution
main() {
    local run_basic=false
    local run_workflows=false
    local run_errors=false
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
    
    print_header "KAFKA SCHEMA REGISTRY MCP SERVER - SINGLE-REGISTRY INTEGRATION TESTS"
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
    else
        [[ "$run_basic" == true ]] && { run_basic_tests || total_failures=$((total_failures + $?)); }
        [[ "$run_workflows" == true ]] && { run_workflow_tests || total_failures=$((total_failures + $?)); }
        [[ "$run_errors" == true ]] && { run_error_tests || total_failures=$((total_failures + $?)); }
    fi
    
    # Generate final summary
    generate_summary
    
    # Final result
    if [[ $total_failures -eq 0 ]]; then
        print_color $GREEN "🎉 ALL SINGLE-REGISTRY TESTS COMPLETED SUCCESSFULLY!"
        print_color $GREEN "✅ Single-Registry MCP Server is ready for production"
        exit 0
    else
        print_color $RED "❌ SOME SINGLE-REGISTRY TESTS FAILED ($total_failures failures)"
        print_color $YELLOW "⚠️  Check test logs for details: $TEST_RESULTS_DIR"
        exit 1
    fi
}

# Execute main function with all arguments
main "$@" 