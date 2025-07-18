#!/bin/bash

# Kafka Schema Registry MCP - Lint Issues Checker
# This script checks for potential lint issues that could cause CI failures
# Based on the CI configuration in .github/workflows/test.yml

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
CRITICAL_ISSUES=0
WARNING_ISSUES=0
TOTAL_CHECKS=0

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "PASS")
            echo -e "${GREEN}✅ PASS${NC}: $message"
            ;;
        "FAIL")
            echo -e "${RED}❌ FAIL${NC}: $message"
            ((CRITICAL_ISSUES++))
            ;;
        "WARN")
            echo -e "${YELLOW}⚠️  WARN${NC}: $message"
            ((WARNING_ISSUES++))
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️  INFO${NC}: $message"
            ;;
    esac
}

# Function to run a command and capture output
run_check() {
    local check_name=$1
    local command=$2
    local critical=${3:-false}
    
    ((TOTAL_CHECKS++))
    echo -e "\n${BLUE}[CHECK $TOTAL_CHECKS]${NC} Running: $check_name"
    echo "Command: $command"
    
    if eval "$command" > /tmp/lint_output 2>&1; then
        print_status "PASS" "$check_name"
        if [[ -s /tmp/lint_output ]]; then
            echo "Output:"
            cat /tmp/lint_output | head -20
            if [[ $(wc -l < /tmp/lint_output) -gt 20 ]]; then
                echo "... (truncated, $(wc -l < /tmp/lint_output) total lines)"
            fi
        fi
    else
        local exit_code=$?
        if [[ "$critical" == "true" ]]; then
            print_status "FAIL" "$check_name (Exit code: $exit_code)"
        else
            print_status "WARN" "$check_name (Exit code: $exit_code)"
        fi
        
        echo "Output:"
        cat /tmp/lint_output | head -30
        if [[ $(wc -l < /tmp/lint_output) -gt 30 ]]; then
            echo "... (truncated, $(wc -l < /tmp/lint_output) total lines)"
        fi
    fi
    
    rm -f /tmp/lint_output
}

# Function to check if tools are installed
check_dependencies() {
    echo -e "${BLUE}=== DEPENDENCY CHECK ===${NC}"
    
    local tools=("python" "flake8" "black" "isort" "mypy")
    local missing_tools=()
    
    for tool in "${tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            local version
            case $tool in
                "python")
                    version=$(python --version 2>&1)
                    ;;
                "flake8")
                    version=$(flake8 --version 2>&1 | head -1)
                    ;;
                "black")
                    version=$(black --version 2>&1)
                    ;;
                "isort")
                    version=$(isort --version 2>&1)
                    ;;
                "mypy")
                    version=$(mypy --version 2>&1)
                    ;;
            esac
            print_status "PASS" "$tool is installed ($version)"
        else
            missing_tools+=("$tool")
            print_status "FAIL" "$tool is not installed"
        fi
    done
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        echo -e "\n${RED}Missing tools detected. Install them with:${NC}"
        echo "pip install flake8 black isort mypy"
        exit 1
    fi
}

# Function to check configuration consistency
check_configuration() {
    echo -e "\n${BLUE}=== CONFIGURATION CHECK ===${NC}"
    
    # Check if pyproject.toml exists
    if [[ -f "pyproject.toml" ]]; then
        print_status "PASS" "pyproject.toml exists"
        
        # Extract line length settings
        local black_line_length=$(grep -A5 "\[tool.black\]" pyproject.toml | grep "line-length" | cut -d'=' -f2 | tr -d ' ' | head -1)
        local ruff_line_length=$(grep -A5 "\[tool.ruff\]" pyproject.toml | grep "line-length" | cut -d'=' -f2 | tr -d ' ' | head -1)
        local isort_line_length=$(grep -A10 "\[tool.isort\]" pyproject.toml | grep "line_length" | cut -d'=' -f2 | tr -d ' ' | head -1)
        
        print_status "INFO" "Black line length: $black_line_length"
        print_status "INFO" "Ruff line length: $ruff_line_length"
        print_status "INFO" "isort line length: $isort_line_length"
        
        # Check CI configuration
        if [[ -f ".github/workflows/test.yml" ]]; then
            local ci_line_length=$(grep "max-line-length" .github/workflows/test.yml | grep -o '[0-9]\+' | tail -1)
            print_status "INFO" "CI flake8 line length: $ci_line_length"
            
            if [[ -n "$ci_line_length" && -n "$black_line_length" && $ci_line_length -ge $black_line_length ]]; then
                print_status "PASS" "CI line length ($ci_line_length) >= Black line length ($black_line_length)"
            elif [[ -n "$ci_line_length" && -n "$black_line_length" ]]; then
                print_status "WARN" "CI line length ($ci_line_length) < Black line length ($black_line_length)"
            else
                print_status "WARN" "Could not extract line length settings properly"
            fi
        fi
    else
        print_status "WARN" "pyproject.toml not found"
    fi
}

# Function to run critical flake8 checks (will fail CI)
check_flake8_critical() {
    echo -e "\n${BLUE}=== FLAKE8 CRITICAL CHECKS (CI BLOCKERS) ===${NC}"
    
    # Critical errors that will fail CI
    run_check "Syntax errors and undefined names" \
        "python -m flake8 *.py tests/*.py --count --select=E9,F63,F7,F82 --show-source --statistics" \
        true
}

# Function to run flake8 style checks (warnings only)
check_flake8_style() {
    echo -e "\n${BLUE}=== FLAKE8 STYLE CHECKS (WARNINGS ONLY) ===${NC}"
    
    # Full flake8 check with same settings as CI
    run_check "Full flake8 style check" \
        "python -m flake8 *.py tests/*.py --count --exit-zero --max-complexity=15 --max-line-length=127 --statistics" \
        false
}

# Function to check Black formatting
check_black_formatting() {
    echo -e "\n${BLUE}=== BLACK FORMATTING CHECK ===${NC}"
    
    run_check "Black formatting check" \
        "python -m black --check --diff *.py tests/*.py" \
        true
}

# Function to check isort import sorting
check_isort_sorting() {
    echo -e "\n${BLUE}=== ISORT IMPORT SORTING CHECK ===${NC}"
    
    run_check "isort import sorting check" \
        "python -m isort --check-only --diff *.py tests/*.py" \
        true
}

# Function to check MyPy type checking (optional)
check_mypy_types() {
    echo -e "\n${BLUE}=== MYPY TYPE CHECKING (OPTIONAL) ===${NC}"
    
    # Check main file only to avoid overwhelming output
    run_check "MyPy type checking (main file)" \
        "python -m mypy kafka_schema_registry_unified_mcp.py --ignore-missing-imports --no-strict-optional" \
        false
}

# Function to provide fix suggestions
suggest_fixes() {
    echo -e "\n${BLUE}=== FIX SUGGESTIONS ===${NC}"
    
    if [[ $CRITICAL_ISSUES -gt 0 ]]; then
        echo -e "${RED}Critical issues found that will fail CI:${NC}"
        echo ""
        echo "To fix formatting issues:"
        echo "  python -m black *.py tests/*.py"
        echo ""
        echo "To fix import sorting issues:"
        echo "  python -m isort *.py tests/*.py"
        echo ""
        echo "To check for syntax errors:"
        echo "  python -m flake8 *.py tests/*.py --select=E9,F63,F7,F82"
        echo ""
    fi
    
    if [[ $WARNING_ISSUES -gt 0 ]]; then
        echo -e "${YELLOW}Warning issues found (won't fail CI but should be addressed):${NC}"
        echo ""
        echo "To see detailed flake8 issues:"
        echo "  python -m flake8 *.py tests/*.py --max-complexity=15 --max-line-length=127"
        echo ""
        echo "To run MyPy type checking:"
        echo "  python -m mypy . --ignore-missing-imports"
        echo ""
    fi
}

# Function to generate summary
generate_summary() {
    echo -e "\n${BLUE}=== SUMMARY ===${NC}"
    echo "Total checks performed: $TOTAL_CHECKS"
    echo -e "Critical issues (will fail CI): ${RED}$CRITICAL_ISSUES${NC}"
    echo -e "Warning issues (won't fail CI): ${YELLOW}$WARNING_ISSUES${NC}"
    
    if [[ $CRITICAL_ISSUES -eq 0 ]]; then
        echo -e "\n${GREEN}🎉 All critical checks passed! Your code should pass CI lint checks.${NC}"
        return 0
    else
        echo -e "\n${RED}💥 Critical issues found! Please fix them before pushing to CI.${NC}"
        return 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -q, --quick         Run only critical checks (skip warnings)"
    echo "  -v, --verbose       Show verbose output"
    echo "  --fix               Automatically fix formatting issues"
    echo "  --no-mypy           Skip MyPy type checking"
    echo ""
    echo "Examples:"
    echo "  $0                  # Run all checks"
    echo "  $0 --quick          # Run only critical checks"
    echo "  $0 --fix            # Fix formatting issues automatically"
}

# Main execution
main() {
    local quick_mode=false
    local fix_mode=false
    local skip_mypy=false
    local verbose=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -q|--quick)
                quick_mode=true
                shift
                ;;
            --fix)
                fix_mode=true
                shift
                ;;
            --no-mypy)
                skip_mypy=true
                shift
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    echo -e "${BLUE}🔍 Kafka Schema Registry MCP - Lint Issues Checker${NC}"
    echo -e "${BLUE}=================================================${NC}"
    
    # Apply fixes if requested
    if [[ "$fix_mode" == "true" ]]; then
        echo -e "\n${BLUE}=== APPLYING FIXES ===${NC}"
        echo "Applying Black formatting..."
        python -m black *.py tests/*.py
        echo "Applying isort import sorting..."
        python -m isort *.py tests/*.py
        echo -e "${GREEN}Fixes applied!${NC}"
        echo ""
    fi
    
    # Run checks
    check_dependencies
    check_configuration
    check_flake8_critical
    check_black_formatting
    check_isort_sorting
    
    if [[ "$quick_mode" == "false" ]]; then
        check_flake8_style
        if [[ "$skip_mypy" == "false" ]]; then
            check_mypy_types
        fi
    fi
    
    suggest_fixes
    generate_summary
}

# Run main function with all arguments
main "$@" 