#!/bin/bash

# Quick Lint Check - One-liner for pre-commit checks
# Runs the most essential checks that will fail CI

echo "🚀 Quick Lint Check..."

# Check critical flake8 issues
if ! python -m flake8 *.py tests/*.py --count --select=E9,F63,F7,F82 --show-source --statistics; then
    echo "❌ Critical flake8 issues found!"
    exit 1
fi

# Check Black formatting
if ! python -m black --check --diff *.py tests/*.py >/dev/null 2>&1; then
    echo "❌ Black formatting issues found!"
    echo "💡 Run: python -m black *.py tests/*.py"
    exit 1
fi

# Check isort import sorting
if ! python -m isort --check-only --diff *.py tests/*.py >/dev/null 2>&1; then
    echo "❌ Import sorting issues found!"
    echo "💡 Run: python -m isort *.py tests/*.py"
    exit 1
fi

echo "✅ All critical checks passed! Ready for CI." 