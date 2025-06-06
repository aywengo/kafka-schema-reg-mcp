#!/bin/bash

# Simple wrapper for unified test runner
# This replaces the need to run separate environment and test scripts

echo "🚀 Kafka Schema Registry MCP Server - Unified Testing"
echo "===================================================="
echo ""
echo "This script replaces the old workflow:"
echo "  ❌ OLD: ./start_multi_registry_environment.sh && ./run_multi_registry_tests.sh"
echo "  ✅ NEW: ./run_all_tests.sh"
echo ""

# Check if user wants quick mode
if [[ "$1" == "--quick" ]] || [[ "$1" == "-q" ]]; then
    echo "🏃 Running in QUICK mode..."
    exec ./run_all_tests.sh --quick
elif [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --quick, -q    Run essential tests only"
    echo "  --help,  -h    Show this help"
    echo ""
    echo "For advanced options, use: ./run_all_tests.sh --help"
    exit 0
else
    echo "🔬 Running FULL test suite..."
    exec ./run_all_tests.sh
fi 