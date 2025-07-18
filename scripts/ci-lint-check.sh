#!/bin/bash

# CI Lint Check - Mirrors exactly what GitHub Actions CI does
# Based on .github/workflows/test.yml lint job

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 CI Lint Check - Mirrors GitHub Actions${NC}"
echo -e "${BLUE}=========================================${NC}"

# Check if we're in the right directory
if [[ ! -f "kafka_schema_registry_unified_mcp.py" ]]; then
    echo -e "${RED}❌ Error: Must be run from project root directory${NC}"
    exit 1
fi

# Function to run a check and report results
run_ci_check() {
    local check_name=$1
    local command=$2
    local should_fail=${3:-true}
    
    echo -e "\n${BLUE}[CI CHECK]${NC} $check_name"
    echo "Command: $command"
    echo "----------------------------------------"
    
    if eval "$command"; then
        echo -e "${GREEN}✅ PASSED${NC}: $check_name"
        return 0
    else
        local exit_code=$?
        if [[ "$should_fail" == "true" ]]; then
            echo -e "${RED}❌ FAILED${NC}: $check_name (Exit code: $exit_code)"
            echo -e "${RED}This will cause CI to fail!${NC}"
            return 1
        else
            echo -e "${YELLOW}⚠️  WARNINGS${NC}: $check_name (Exit code: $exit_code, but CI continues)"
            return 0
        fi
    fi
}

# Step 1: Install dependencies (informational)
echo -e "\n${BLUE}=== STEP 1: Dependencies ===${NC}"
echo "In CI, these tools are installed:"
echo "  pip install flake8 black isort mypy"
echo ""
echo "Checking if tools are available locally:"
for tool in flake8 black isort mypy; do
    if command -v "$tool" &> /dev/null; then
        echo -e "${GREEN}✅${NC} $tool is available"
    else
        echo -e "${RED}❌${NC} $tool is not available"
    fi
done

# Step 2: Lint with flake8 (CRITICAL - will fail CI)
echo -e "\n${BLUE}=== STEP 2: Flake8 Critical Errors ===${NC}"
echo "This check will FAIL CI if it finds issues"

if ! run_ci_check "Flake8 critical errors" \
    "flake8 *.py tests/*.py --count --select=E9,F63,F7,F82 --show-source --statistics" \
    true; then
    CRITICAL_FAILED=true
fi

# Step 3: Flake8 style warnings (will NOT fail CI)
echo -e "\n${BLUE}=== STEP 3: Flake8 Style Warnings ===${NC}"
echo "This check will NOT fail CI (--exit-zero), but shows warnings"

run_ci_check "Flake8 style warnings" \
    "flake8 *.py tests/*.py --count --exit-zero --max-complexity=15 --max-line-length=127 --statistics" \
    false

# Step 4: Black formatting check (CRITICAL - will fail CI)
echo -e "\n${BLUE}=== STEP 4: Black Formatting ===${NC}"
echo "This check will FAIL CI if code is not properly formatted"

if ! run_ci_check "Black formatting" \
    "black --check --diff *.py tests/*.py" \
    true; then
    CRITICAL_FAILED=true
fi

# Step 5: isort import sorting (CRITICAL - will fail CI)
echo -e "\n${BLUE}=== STEP 5: isort Import Sorting ===${NC}"
echo "This check will FAIL CI if imports are not properly sorted"

if ! run_ci_check "isort import sorting" \
    "isort --check-only --diff *.py tests/*.py" \
    true; then
    CRITICAL_FAILED=true
fi

# Summary
echo -e "\n${BLUE}=== SUMMARY ===${NC}"
if [[ "${CRITICAL_FAILED:-false}" == "true" ]]; then
    echo -e "${RED}💥 CRITICAL ISSUES FOUND${NC}"
    echo -e "${RED}Your code will FAIL the CI lint job!${NC}"
    echo ""
    echo -e "${YELLOW}Quick fixes:${NC}"
    echo "  # Fix formatting:"
    echo "  python -m black *.py tests/*.py"
    echo "  python -m isort *.py tests/*.py"
    echo ""
    echo "  # Check for syntax errors:"
    echo "  python -m flake8 *.py tests/*.py --select=E9,F63,F7,F82"
    echo ""
    exit 1
else
    echo -e "${GREEN}🎉 All critical checks passed!${NC}"
    echo -e "${GREEN}Your code should pass the CI lint job.${NC}"
    echo ""
    echo -e "${BLUE}Note:${NC} You may have style warnings, but those won't fail CI."
    echo "Run the full check with: ./scripts/check-lint-issues.sh"
    exit 0
fi 