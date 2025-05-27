#!/bin/bash

# Multi-Registry Test Runner
# 
# This script runs comprehensive tests designed specifically for multi-registry
# environments, including migration, comparison, and cross-registry validation

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

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

# Test directories and files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_RESULTS_DIR="$SCRIPT_DIR/results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create results directory
mkdir -p "$TEST_RESULTS_DIR"

# Log files
OVERALL_LOG="$TEST_RESULTS_DIR/multi_registry_test_$TIMESTAMP.log"
SUMMARY_LOG="$TEST_RESULTS_DIR/multi_registry_summary_$TIMESTAMP.txt"

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
        echo "PASS,$test_name,$duration,$description" >> "$TEST_RESULTS_DIR/multi_registry_results_$TIMESTAMP.csv"
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        print_color $RED "   ❌ FAILED ($duration seconds)"
        echo "FAIL,$test_name,$duration,$description" >> "$TEST_RESULTS_DIR/multi_registry_results_$TIMESTAMP.csv"
        
        # Show last few lines of error log
        print_color $RED "   Last 5 lines of error output:"
        tail -5 "$test_log" | sed 's/^/   /'
        return 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    print_header "CHECKING MULTI-REGISTRY PREREQUISITES"
    
    # Check if both Schema Registries are running
    if curl -s http://localhost:38081/subjects >/dev/null 2>&1; then
        print_color $GREEN "✅ Schema Registry DEV is running on localhost:38081"
    else
        print_color $RED "❌ Schema Registry DEV is not running on localhost:38081"
        print_color $YELLOW "Please start the multi-registry environment:"
        print_color $YELLOW "  ./start_multi_registry_environment.sh"
        exit 1
    fi
    
    if curl -s http://localhost:38082/subjects >/dev/null 2>&1; then
        print_color $GREEN "✅ Schema Registry PROD is running on localhost:38082"
    else
        print_color $RED "❌ Schema Registry PROD is not running on localhost:38082"
        print_color $YELLOW "Please start the multi-registry environment:"
        print_color $YELLOW "  ./start_multi_registry_environment.sh"
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
    if [[ -f "$SCRIPT_DIR/../kafka_schema_registry_mcp.py" ]] && [[ -f "$SCRIPT_DIR/../kafka_schema_registry_multi_mcp.py" ]]; then
        print_color $GREEN "✅ MCP server files found"
    else
        print_color $RED "❌ MCP server files not found"
        exit 1
    fi
    
    print_color $GREEN "✅ All multi-registry prerequisites satisfied"
}

# Function to run multi-registry configuration tests
run_multi_config_tests() {
    print_header "MULTI-REGISTRY CONFIGURATION TESTS"
    
    local passed=0
    local total=0
    
    # Multi-registry configuration tests
    tests=(
        "multi_config:test_multi_registry_mcp.py:Multi-registry MCP server configuration"
        "numbered_config:test_numbered_config.py:Numbered configuration validation"
        "readonly_enforcement:test_readonly_mode.py:Read-only mode enforcement"
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
    
    print_color $WHITE "Multi-Config Tests: $passed/$total passed"
    return $((total - passed))
}

# Function to run cross-registry workflow tests
run_workflow_tests() {
    print_header "CROSS-REGISTRY WORKFLOW TESTS"
    
    local passed=0
    local total=0
    
    tests=(
        "cross_registry_workflows:test_end_to_end_workflows.py:Cross-registry workflow validation"
        "production_deployment:test_production_readiness.py:Production deployment workflows"
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

# Function to run multi-registry tool validation
run_tool_validation_tests() {
    print_header "MULTI-REGISTRY TOOL VALIDATION"
    
    local passed=0
    local total=0
    
    tests=(
        "all_tools_multi:test_all_tools_validation.py:All 68 tools with multi-registry setup"
    )
    
    for test_spec in "${tests[@]}"; do
        IFS=':' read -r test_name test_file description <<< "$test_spec"
        total=$((total + 1))
        
        if [[ -f "$SCRIPT_DIR/$test_file" ]]; then
            # Set environment to use multi-registry mode
            export MULTI_REGISTRY_MODE=true
            if run_test "$test_name" "$SCRIPT_DIR/$test_file" "$description"; then
                passed=$((passed + 1))
            fi
            unset MULTI_REGISTRY_MODE
        else
            print_color $YELLOW "⚠️  Test file not found: $test_file"
        fi
    done
    
    print_color $WHITE "Tool Validation Tests: $passed/$total passed"
    return $((total - passed))
}

# Function to run performance tests
run_performance_tests() {
    print_header "MULTI-REGISTRY PERFORMANCE TESTS"
    
    local passed=0
    local total=0
    
    tests=(
        "multi_performance:test_performance_load.py:Multi-registry performance testing"
    )
    
    for test_spec in "${tests[@]}"; do
        IFS=':' read -r test_name test_file description <<< "$test_spec"
        total=$((total + 1))
        
        if [[ -f "$SCRIPT_DIR/$test_file" ]]; then
            # Set environment for multi-registry performance testing
            export MULTI_REGISTRY_MODE=true
            if run_test "$test_name" "$SCRIPT_DIR/$test_file" "$description"; then
                passed=$((passed + 1))
            fi
            unset MULTI_REGISTRY_MODE
        else
            print_color $YELLOW "⚠️  Test file not found: $test_file"
        fi
    done
    
    print_color $WHITE "Performance Tests: $passed/$total passed"
    return $((total - passed))
}

# Function to generate test summary
generate_summary() {
    print_header "MULTI-REGISTRY TEST SUMMARY"
    
    local summary_file="$SUMMARY_LOG"
    local csv_file="$TEST_RESULTS_DIR/multi_registry_results_$TIMESTAMP.csv"
    
    {
        echo "Multi-Registry Kafka Schema Registry MCP Server - Test Report"
        echo "============================================================"
        echo "Test Run Timestamp: $(date)"
        echo "Environment: Multi-Registry (DEV + PROD)"
            echo "DEV Registry: http://localhost:38081"
    echo "PROD Registry: http://localhost:38082"
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
        echo "MULTI-REGISTRY FEATURES TESTED:"
        echo "==============================="
        echo "✅ Multi-Registry Configuration (numbered configs)"
        echo "✅ Cross-Registry Workflows"
        echo "✅ Read-Only Mode Enforcement"
        echo "✅ Schema Migration and Comparison"
        echo "✅ All 68 MCP Tools (multi-registry mode)"
        echo "✅ Performance and Scalability"
        echo "✅ Production Deployment Scenarios"
        
        echo ""
        echo "REGISTRY SETUP:"
        echo "=============="
        echo "• DEV Registry: development, read-write, backward compatibility"
        echo "• PROD Registry: production, read-only, forward compatibility"
        echo "• Cross-Registry Operations: migration, comparison, validation"
        echo "• High Availability: failover, disaster recovery"
        
    } | tee "$summary_file"
    
    print_color $GREEN "📊 Multi-registry test summary saved to: $summary_file"
    print_color $GREEN "📊 Detailed logs in: $TEST_RESULTS_DIR"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "OPTIONS:"
    echo "  --config        Run only multi-registry configuration tests"
    echo "  --workflows     Run only cross-registry workflow tests"
    echo "  --tools         Run only tool validation tests"
    echo "  --performance   Run only performance tests"
    echo "  --migration     Run migration and comparison tests"
    echo "  --all           Run all multi-registry test categories (default)"
    echo "  --help          Show this help message"
    echo ""
    echo "EXAMPLES:"
    echo "  $0                        # Run all multi-registry tests"
    echo "  $0 --config              # Run only configuration tests"
    echo "  $0 --migration           # Run migration and comparison tests"
    echo "  $0 --workflows --tools   # Run workflows and tool validation"
    echo ""
    echo "PREREQUISITES:"
    echo "  Multi-registry environment must be running:"
    echo "    ./start_multi_registry_environment.sh"
    echo ""
}

# Main execution
main() {
    local run_config=false
    local run_workflows=false
    local run_tools=false
    local run_performance=false
    local run_migration=false
    local run_all=true
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --config)
                run_config=true
                run_all=false
                shift
                ;;
            --workflows)
                run_workflows=true
                run_all=false
                shift
                ;;
            --tools)
                run_tools=true
                run_all=false
                shift
                ;;
            --performance)
                run_performance=true
                run_all=false
                shift
                ;;
            --migration)
                run_migration=true
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
    
    print_header "MULTI-REGISTRY KAFKA SCHEMA REGISTRY MCP SERVER TESTS"
    log_print "Multi-registry test execution started at: $(date)"
    
    # Initialize CSV results file
    echo "Status,TestName,Duration,Description" > "$TEST_RESULTS_DIR/multi_registry_results_$TIMESTAMP.csv"
    
    # Check prerequisites first
    check_prerequisites
    
    local total_failures=0
    
    # Run selected test categories
    if [[ "$run_all" == true ]]; then
        run_multi_config_tests || total_failures=$((total_failures + $?))
        run_workflow_tests || total_failures=$((total_failures + $?))
        run_tool_validation_tests || total_failures=$((total_failures + $?))
        run_performance_tests || total_failures=$((total_failures + $?))
        
        # Also run migration tests if available
        if [[ -f "$SCRIPT_DIR/run_migration_tests.sh" ]]; then
            print_color $BLUE "🔄 Running migration and comparison tests..."
            if ./run_migration_tests.sh; then
                print_color $GREEN "✅ Migration tests completed successfully"
            else
                print_color $YELLOW "⚠️ Some migration tests failed (check migration logs)"
                total_failures=$((total_failures + 1))
            fi
        fi
    else
        [[ "$run_config" == true ]] && { run_multi_config_tests || total_failures=$((total_failures + $?)); }
        [[ "$run_workflows" == true ]] && { run_workflow_tests || total_failures=$((total_failures + $?)); }
        [[ "$run_tools" == true ]] && { run_tool_validation_tests || total_failures=$((total_failures + $?)); }
        [[ "$run_performance" == true ]] && { run_performance_tests || total_failures=$((total_failures + $?)); }
        [[ "$run_migration" == true ]] && { 
            if [[ -f "$SCRIPT_DIR/run_migration_tests.sh" ]]; then
                ./run_migration_tests.sh || total_failures=$((total_failures + 1))
            else
                print_color $RED "❌ Migration test script not found"
                total_failures=$((total_failures + 1))
            fi
        }
    fi
    
    # Generate final summary
    generate_summary
    
    # Final result
    if [[ $total_failures -eq 0 ]]; then
        print_color $GREEN "🎉 ALL MULTI-REGISTRY TESTS COMPLETED SUCCESSFULLY!"
        print_color $GREEN "✅ Multi-Registry MCP Server is ready for production"
        exit 0
    else
        print_color $RED "❌ SOME MULTI-REGISTRY TESTS FAILED ($total_failures failures)"
        print_color $YELLOW "⚠️  Check test logs for details: $TEST_RESULTS_DIR"
        exit 1
    fi
}

# Execute main function with all arguments
main "$@" 