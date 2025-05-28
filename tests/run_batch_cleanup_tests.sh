#!/bin/bash

# Batch Cleanup Tests Runner
# 
# Simple wrapper for running batch cleanup tests in the current environment.
# Can be used standalone or integrated into other test suites.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🧹 Running Batch Cleanup Tests"
echo "=============================="

# Check which environment we're in
if [ -n "${SCHEMA_REGISTRY_NAME_1:-}" ] && [ -n "${SCHEMA_REGISTRY_URL_1:-}" ]; then
    echo "🌐 Multi-registry environment detected"
    MODE="multi"
elif [ -n "${SCHEMA_REGISTRY_URL:-}" ]; then
    echo "📍 Single-registry environment detected"
    MODE="single"
else
    echo -e "${RED}❌ No registry environment detected${NC}"
    echo "Please set SCHEMA_REGISTRY_URL or multi-registry environment variables"
    exit 1
fi

# Run appropriate tests based on environment
if [ "$MODE" = "multi" ]; then
    # In multi-registry mode, run the full multi-registry batch cleanup suite
    if [ -f "$SCRIPT_DIR/run_multi_registry_batch_cleanup_tests.sh" ]; then
        echo "Running multi-registry batch cleanup tests..."
        exec "$SCRIPT_DIR/run_multi_registry_batch_cleanup_tests.sh" "$@"
    else
        echo -e "${RED}❌ Multi-registry batch cleanup test script not found${NC}"
        exit 1
    fi
else
    # In single-registry mode, run basic batch cleanup tests
    echo "Running single-registry batch cleanup tests..."
    
    # Run the integration test suite
    if command -v pytest &> /dev/null; then
        echo "Using pytest for comprehensive testing..."
        python3 -m pytest tests/test_batch_cleanup_integration.py::TestBatchCleanupIntegration::test_dry_run_default_safety -v
        python3 -m pytest tests/test_batch_cleanup_integration.py::TestBatchCleanupIntegration::test_explicit_dry_run_false -v
        python3 -m pytest tests/test_batch_cleanup_integration.py::TestBatchCleanupIntegration::test_empty_context_handling -v
        python3 -m pytest tests/test_batch_cleanup_integration.py::TestBatchCleanupIntegration::test_readonly_mode_protection -v
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Batch cleanup tests passed!${NC}"
            exit 0
        else
            echo -e "${RED}❌ Batch cleanup tests failed!${NC}"
            exit 1
        fi
    else
        # Fallback to basic test script
        if [ -f "tests/test_batch_cleanup.py" ]; then
            python3 tests/test_batch_cleanup.py
            exit $?
        else
            echo -e "${YELLOW}⚠️  No batch cleanup tests available for single-registry mode${NC}"
            exit 0
        fi
    fi
fi 