# Development Guidelines

> **Audience**: LLM-driven engineering agents and human developers working on the Kafka Schema Registry MCP project.

## Prerequisites

Before starting development, ensure you have:

- **Python 3.10+** (project minimum: 3.10, CI uses 3.11)
- **Docker Desktop** (required for running tests)
- **Required ports available:** 38080-38082, 9092, 39093
- **Development tools:** `flake8`, `black`, `isort`, `mypy` (optional)

### Quick Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install dev dependencies (optional but recommended)
pip install flake8 black isort mypy

# Or install from pyproject.toml
pip install -e ".[dev]"
```

## Repository Structure

The repository is organized into the following directories:

- `tests/`: Contains comprehensive test suites and test runners. See [tests/README.md](tests/README.md)
- `.github/`: Contains GitHub Actions workflow files for CI/CD
- `scripts/`: Contains lint checking and utility scripts. See [scripts/README.md](scripts/README.md)
- `config-examples/`: Contains configuration examples for Claude Desktop and other MCP clients
- `docs/`: Contains comprehensive documentation
- `helm/`: Contains Helm charts for Kubernetes deployment
- `kubernetes/`: Contains Kubernetes deployment files
- `pyproject.toml`: Project configuration (Black, Ruff, isort, MyPy settings)
- `TESTING_SETUP_GUIDE.md`: Comprehensive testing setup guide

## Pre-Commit Checklist

Before committing any changes, **ALWAYS** run linting checks to ensure code quality and consistency.

### Quick Pre-Commit Check (Required)

For fastest feedback before committing:

```bash
./scripts/quick-lint-check.sh
```

**What it does:** Ultra-fast check (~2-3 seconds) for critical issues that will fail CI:
- Flake8 critical errors (E9, F63, F7, F82)
- Black formatting
- isort import sorting

**If it fails:** Use the comprehensive check below to fix issues.

### Comprehensive Pre-Commit Check

For detailed checking and automatic fixes:

```bash
# Run comprehensive check with auto-fix
./scripts/check-lint-issues.sh --fix

# Or run without auto-fix to see what would change
./scripts/check-lint-issues.sh
```

**What it does:** Comprehensive lint checking with:
- Dependency verification
- Configuration consistency checks
- All critical checks (same as CI)
- Optional MyPy type checking
- Automatic fix suggestions

**Options:**
- `--fix`: Automatically fix formatting issues (Black + isort)
- `--quick`: Run only critical checks (skip warnings)
- `--no-mypy`: Skip MyPy type checking

### CI Mirror Check (Required Before Pushing)

To verify your code will pass CI exactly:

```bash
./scripts/ci-lint-check.sh
```

**What it does:** Mirrors exactly what the GitHub Actions CI lint job does:
- Flake8 critical errors (will fail CI)
- Flake8 style warnings (won't fail CI, but shown)
- Black formatting check (will fail CI)
- isort import sorting (will fail CI)

**Exit codes:**
- `0` = All critical checks passed (CI will pass)
- `1` = Critical issues found (CI will fail)

### Running Tests (Before Pushing)

**Prerequisites for tests:**
- Docker Desktop must be running
- Ports 38080-38082 and 9092 must be available
- At least 4GB RAM allocated to Docker

```bash
# Quick test run (essential tests only)
cd tests
./run_all_tests.sh --quick

# Full test suite (comprehensive)
./run_all_tests.sh

# Keep environment running for debugging
./run_all_tests.sh --no-cleanup
```

**What it does:** 
- Starts unified test environment (multi-registry mode)
- Runs comprehensive test suite
- Generates detailed reports
- Cleans up environment (unless `--no-cleanup`)

See [tests/README.md](tests/README.md) and [TESTING_SETUP_GUIDE.md](TESTING_SETUP_GUIDE.md) for detailed testing information.

## Lint Script Comparison

| Script | Speed | Use Case | Auto-Fix |
|--------|-------|----------|----------|
| `quick-lint-check.sh` | ~2-3s | Pre-commit hook | ❌ |
| `ci-lint-check.sh` | ~10-15s | Before pushing | ❌ |
| `check-lint-issues.sh` | ~20-30s | Comprehensive check | ✅ (`--fix`) |

**Recommendation:** Use `quick-lint-check.sh` frequently during development, and `ci-lint-check.sh` before pushing.

## Important Notes

1. **Always run checks before committing** - This ensures consistency with the CI/CD pipeline
2. **Fix critical errors immediately** - E9, F63, F7, F82 errors indicate real problems
3. **Auto-fix when possible** - Use `--fix` flag with `check-lint-issues.sh` to auto-fix formatting
4. **Check the diff** - Review what Black/isort would change before applying fixes
5. **Match CI configuration** - These checks mirror the GitHub Actions workflow exactly
6. **Docker required for tests** - Full test suite requires Docker Desktop running

## Project Configuration

All configuration is in `pyproject.toml`:

- **Black line length:** 120 characters
- **Ruff line length:** 120 characters  
- **isort line length:** 120 characters
- **isort profile:** black (compatible with Black formatting)
- **Flake8 max line length:** 127 characters (more permissive than Black)
- **Flake8 max complexity:** 15
- **MyPy:** Optional, configured but not enforced in CI

**⚠️ Important:** Never change lint tool configurations in `pyproject.toml`. Write code that passes the existing rules.

## Common Fixes

### Formatting Issues
```bash
# Auto-fix formatting
python -m black *.py tests/*.py
python -m isort *.py tests/*.py

# Or use the script
./scripts/check-lint-issues.sh --fix
```

### Critical Errors
```bash
# Check for syntax errors and undefined names
python -m flake8 *.py tests/*.py --select=E9,F63,F7,F82

# Full flake8 check (warnings won't fail CI)
python -m flake8 *.py tests/*.py --max-complexity=15 --max-line-length=127
```

## When to Skip Checks

Only skip these checks if:
- You're making **documentation-only changes** (no Python code)
- You're in an **emergency hotfix situation** (but fix formatting in follow-up PR)

Otherwise, **always run the checks before committing**.

## Additional Resources

- **Lint Scripts Documentation:** [scripts/README.md](scripts/README.md)
- **Testing Guide:** [tests/README.md](tests/README.md) and [TESTING_SETUP_GUIDE.md](TESTING_SETUP_GUIDE.md)
- **CI Workflow:** [.github/workflows/test.yml](.github/workflows/test.yml)
- **Project Configuration:** [pyproject.toml](pyproject.toml)
