# Lint Checking Scripts

This directory contains scripts to check for potential lint issues that could cause CI failures.

## Scripts

### 1. `quick-lint-check.sh` - Fast Pre-commit Check

**Purpose**: Ultra-fast check for critical issues before committing.

**Usage**:
```bash
./scripts/quick-lint-check.sh
```

**What it checks**:
- ✅ **Flake8 critical errors** (E9, F63, F7, F82) - **WILL FAIL CI**
- ✅ **Black formatting** - **WILL FAIL CI**
- ✅ **isort import sorting** - **WILL FAIL CI**

**Features**:
- Minimal output for speed
- Provides fix suggestions on failure
- Perfect for git pre-commit hooks
- Runs in ~2-3 seconds

### 2. `ci-lint-check.sh` - CI Mirror Check

**Purpose**: Mirrors exactly what the GitHub Actions CI lint job does.

**Usage**:
```bash
./scripts/ci-lint-check.sh
```

**What it checks**:
- ✅ **Flake8 critical errors** (E9, F63, F7, F82) - **WILL FAIL CI**
- ⚠️  **Flake8 style warnings** (all other issues) - **Won't fail CI**
- ✅ **Black formatting** - **WILL FAIL CI** 
- ✅ **isort import sorting** - **WILL FAIL CI**

**Exit codes**:
- `0` = All critical checks passed (CI will pass)
- `1` = Critical issues found (CI will fail)

### 3. `check-lint-issues.sh` - Comprehensive Check

**Purpose**: Comprehensive lint checking with additional features.

**Usage**:
```bash
# Run all checks
./scripts/check-lint-issues.sh

# Run only critical checks (faster)
./scripts/check-lint-issues.sh --quick

# Automatically fix formatting issues
./scripts/check-lint-issues.sh --fix

# Skip MyPy type checking
./scripts/check-lint-issues.sh --no-mypy

# Show help
./scripts/check-lint-issues.sh --help
```

**What it checks**:
- ✅ **Dependency verification** - Check if tools are installed
- ✅ **Configuration consistency** - Check pyproject.toml vs CI settings
- ✅ **Flake8 critical errors** - **WILL FAIL CI**
- ✅ **Black formatting** - **WILL FAIL CI**
- ✅ **isort import sorting** - **WILL FAIL CI**
- ⚠️  **Flake8 style warnings** - **Won't fail CI**
- ⚠️  **MyPy type checking** - **Optional**

**Features**:
- Colored output with clear status indicators
- Detailed error reporting with truncated output
- Automatic fix mode (`--fix`)
- Configuration validation
- Comprehensive summary and fix suggestions

## Quick Start

### Before Pushing to CI
```bash
# Ultra-fast check (2-3 seconds)
./scripts/quick-lint-check.sh

# Or detailed CI mirror check
./scripts/ci-lint-check.sh
```

### During Development
```bash
# Fix formatting issues automatically
./scripts/check-lint-issues.sh --fix

# Run comprehensive check
./scripts/check-lint-issues.sh
```

### CI Troubleshooting
```bash
# If CI fails, run this to see exactly what CI sees
./scripts/ci-lint-check.sh

# Fix the issues
./scripts/check-lint-issues.sh --fix

# Verify fixes
./scripts/ci-lint-check.sh
```

## Understanding CI Lint Behavior

### Critical Checks (Will Fail CI)
These checks will cause the CI lint job to fail with exit code 1:

1. **Flake8 Critical Errors** (`E9,F63,F7,F82`)
   - Syntax errors
   - Undefined names
   - Import issues

2. **Black Formatting**
   - Code not formatted according to Black standards
   - Line length violations (>120 chars for Black)

3. **isort Import Sorting**
   - Imports not sorted according to isort configuration
   - Missing trailing commas in imports

### Warning Checks (Won't Fail CI)
These generate warnings but CI continues (`--exit-zero`):

- Line length violations (>127 chars for flake8)
- Complexity violations (>15 for functions)
- Unused variables/imports
- Style issues (whitespace, etc.)

## Configuration

The scripts read configuration from:
- `pyproject.toml` - Black, Ruff, isort, MyPy settings
- `.github/workflows/test.yml` - CI flake8 settings

### Current Configuration
- **Black**: 120 characters line length
- **Ruff**: 120 characters line length  
- **isort**: 120 characters line length
- **CI flake8**: 127 characters line length (more permissive)

## Common Issues and Fixes

### Black Formatting Issues
```bash
# Fix automatically
python -m black *.py tests/*.py

# Check what would be changed
python -m black --check --diff *.py tests/*.py
```

### isort Import Issues
```bash
# Fix automatically
python -m isort *.py tests/*.py

# Check what would be changed
python -m isort --check-only --diff *.py tests/*.py
```

### Flake8 Critical Errors
```bash
# Check for critical errors only
python -m flake8 *.py tests/*.py --select=E9,F63,F7,F82

# Full flake8 check
python -m flake8 *.py tests/*.py --max-complexity=15 --max-line-length=127
```

## Integration with Development Workflow

### Pre-commit Hook (Recommended)
```bash
# Add to .git/hooks/pre-commit
#!/bin/bash
./scripts/quick-lint-check.sh
```

### VS Code Integration
Add to `.vscode/tasks.json`:
```json
{
    "label": "Lint Check",
    "type": "shell",
    "command": "./scripts/ci-lint-check.sh",
    "group": "test"
}
```

### GitHub Actions Integration
The scripts mirror the exact commands used in `.github/workflows/test.yml`:

```yaml
- name: Lint with flake8
  run: |
    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
    flake8 . --count --exit-zero --max-complexity=15 --max-line-length=127 --statistics

- name: Check code formatting with black
  run: |
    black --check --diff *.py tests/*.py

- name: Check import sorting with isort
  run: |
    isort --check-only --diff *.py tests/*.py
```

## Troubleshooting

### "Tool not found" errors
```bash
# Install missing tools
pip install flake8 black isort mypy

# Or install dev dependencies
pip install -e ".[dev]"
```

### Permission denied
```bash
# Make scripts executable
chmod +x scripts/*.sh
```

### Different results locally vs CI
- Ensure you're using the same Python version as CI (3.11)
- Check that all tools are installed with correct versions
- Run `./scripts/ci-lint-check.sh` which mirrors CI exactly

## Script Output Examples

### Successful Check
```
🔍 CI Lint Check - Mirrors GitHub Actions
=========================================

✅ All critical checks passed!
Your code should pass the CI lint job.
```

### Failed Check
```
❌ FAILED: Black formatting (Exit code: 1)
This will cause CI to fail!

💥 CRITICAL ISSUES FOUND
Your code will FAIL the CI lint job!

Quick fixes:
  python -m black *.py tests/*.py
  python -m isort *.py tests/*.py
``` 