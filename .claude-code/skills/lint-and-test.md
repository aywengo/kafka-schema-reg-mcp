# Lint and Test Skill

**Skill Name:** `/lint-and-test`
**Category:** Quality Assurance
**Description:** Run comprehensive linting and testing workflow with auto-fix capabilities

## Purpose

This skill automates the complete code quality workflow including linting, formatting, and testing. It's designed to be run before commits and pushes to ensure code meets project standards.

## Usage

```
/lint-and-test [mode]
```

### Modes

- `quick` - Fast lint check only (~2-3 seconds)
- `fix` - Lint with auto-fix (~20-30 seconds)
- `ci` - CI mirror check (~10-15 seconds)
- `test-quick` - Lint + quick tests (~5 minutes)
- `test-full` - Lint + full test suite (~15 minutes)
- `pre-commit` - Pre-commit workflow (default)
- `pre-push` - Pre-push workflow

### Examples

```
/lint-and-test quick

/lint-and-test fix

/lint-and-test ci

/lint-and-test test-quick

/lint-and-test pre-push
```

## What This Skill Does

### Quick Mode (Default)
1. Runs `./scripts/quick-lint-check.sh`
2. Checks Black formatting
3. Checks isort import ordering
4. Shows violations without fixing
5. Returns pass/fail status

**Use before:** Every commit
**Duration:** 2-3 seconds

### Fix Mode
1. Runs `./scripts/check-lint-issues.sh --fix`
2. Auto-formats with Black (line length 120)
3. Auto-sorts imports with isort (profile: black)
4. Runs Ruff linter (line length 120, complexity ≤15)
5. Runs Flake8 (max line 127, complexity ≤15)
6. Shows remaining issues
7. Reports what was fixed

**Use before:** Commits with formatting issues
**Duration:** 20-30 seconds

### CI Mode
1. Runs `./scripts/ci-lint-check.sh`
2. Mirrors exact CI pipeline checks
3. No auto-fixing (fail if violations exist)
4. Comprehensive validation
5. Must pass before pushing

**Use before:** Every push
**Duration:** 10-15 seconds

### Test-Quick Mode
1. Runs quick lint check
2. Activates virtual environment
3. Runs `cd tests && ./run_all_tests.sh --quick`
4. Essential tests only (35 tests)
5. Shows pass/fail summary

**Use before:** Major commits
**Duration:** ~5 minutes

### Test-Full Mode
1. Runs CI lint check
2. Activates virtual environment
3. Runs full test suite
4. All test categories
5. Generates test reports

**Use before:** Pull requests
**Duration:** ~15 minutes

### Pre-Commit Mode (Default)
```
Workflow:
  1. Quick lint check (2-3s)
     ↓
  2. If issues found → Fix mode (20-30s)
     ↓
  3. Verify fixes → Quick lint check again
     ↓
  4. Show git diff of changes
     ↓
  5. Ready to commit ✅
```

### Pre-Push Mode
```
Workflow:
  1. CI lint check (10-15s)
     ↓
  2. If issues found → FAIL (must fix first)
     ↓
  3. Quick tests (optional, 5 min)
     ↓
  4. Show commit log
     ↓
  5. Ready to push ✅
```

## Linting Tools Configuration

### Black (Code Formatter)
```python
[tool.black]
line-length = 120
target-version = ['py310']
```
- Formats code automatically
- Consistent style across project
- No configuration choices needed

### isort (Import Sorter)
```python
[tool.isort]
profile = "black"
line_length = 120
```
- Sorts and groups imports
- Compatible with Black
- Standard library → third-party → local

### Ruff (Fast Linter)
```python
[tool.ruff]
line-length = 120
select = ["E", "F", "W", "I"]
```
- Fast Python linter (Rust-based)
- Checks code quality
- Complexity limit: 15

### Flake8 (Style Checker)
```python
[tool.flake8]
max-line-length = 127
max-complexity = 15
```
- Style guide enforcement (PEP 8)
- Cyclomatic complexity checking
- Additional safety checks

### MyPy (Type Checker) - Optional
```python
[tool.mypy]
python_version = "3.10"
warn_return_any = true
```
- Static type checking
- Not enforced in CI
- Recommended for new code

## Testing Framework

### Test Categories

**Essential Tests** (Quick mode):
- Basic unified server tests (9 tests)
- Essential integration tests (15 tests)
- Multi-registry core tests (3 tests)
- MCP container integration (1 test)
- MCP 2025-06-18 compliance (5 tests)
- SLIM_MODE integration (1 test)
- Smart defaults (1 test)
- **Total: 35 tests**

**Comprehensive Tests** (Full mode):
- All essential tests
- Performance tests
- Production scenario tests
- Edge case handling
- Stress testing
- **Total: 80+ tests**

### Test Requirements

Before running tests:
```markdown
□ Docker Desktop is running
□ Ports available: 38080-38082, 9092, 39093
□ Virtual environment activated
□ At least 4GB RAM for Docker
□ No other Schema Registry instances running
```

### Test Output

```
Test Results Summary
====================
Total Tests: 35
Passed: 35 ✅
Failed: 0
Skipped: 0
Duration: 70 seconds
Success Rate: 100.0%

Test Environment:
  DEV Registry: http://localhost:38081 ✅
  PROD Registry: http://localhost:38082 ✅
  Docker: 4 containers running ✅
```

## Error Handling

### Linting Errors

**Black formatting issues:**
```
Error: File would be reformatted
Fix: Run /lint-and-test fix
```

**Import ordering issues:**
```
Error: Imports are not sorted
Fix: Run /lint-and-test fix
```

**Ruff violations:**
```
Error: F401 'module' imported but unused
Fix: Remove unused import manually
```

**Flake8 violations:**
```
Error: E501 line too long (130 > 127 characters)
Fix: Break line or run Black formatter
```

**Complexity warnings:**
```
Error: C901 'function' is too complex (20)
Fix: Refactor function into smaller pieces
```

### Testing Errors

**Docker not running:**
```
Error: Cannot connect to Docker daemon
Fix: Start Docker Desktop
```

**Port conflicts:**
```
Error: Port 38081 already in use
Fix:
  lsof -i :38081
  kill -9 <PID>
```

**Import errors:**
```
Error: ModuleNotFoundError: No module named 'fastmcp'
Fix:
  source .venv/bin/activate
  pip install -r requirements.txt
```

**Test failures:**
```
Error: test_compatibility_check FAILED
Action:
  1. Check test output for details
  2. Run with --verbose flag
  3. Keep environment running: --no-cleanup
  4. Debug the failing test
```

## Output Examples

### Quick Lint (Pass)
```
✅ All critical checks passed! Ready for CI.

Checks performed:
  ✅ Black formatting
  ✅ isort import ordering

Duration: 2.3 seconds
```

### Quick Lint (Fail)
```
❌ Linting issues found

Issues:
  ❌ Black would reformat 3 files:
     - kafka_schema_registry_unified_mcp.py
     - remote-mcp-server.py
     - tests/test_unified_server.py

  ❌ isort would reorder imports in 2 files:
     - kafka_schema_registry_unified_mcp.py
     - tests/test_integration.py

Recommended action:
  Run: /lint-and-test fix
```

### Fix Mode
```
🔧 Running lint fixes...

Black formatter:
  ✅ Reformatted kafka_schema_registry_unified_mcp.py
  ✅ Reformatted remote-mcp-server.py
  ✅ Reformatted tests/test_unified_server.py

isort:
  ✅ Fixed imports in kafka_schema_registry_unified_mcp.py
  ✅ Fixed imports in tests/test_integration.py

Ruff:
  ✅ No issues found

Flake8:
  ✅ No violations

✅ All issues fixed! Run git diff to review changes.
```

### CI Mode (Pass)
```
✅ CI Lint Check Passed

All checks:
  ✅ Black formatting (120 char limit)
  ✅ isort import ordering (profile: black)
  ✅ Ruff linting (complexity ≤15)
  ✅ Flake8 style check (max line 127)

✅ Ready to push!
```

### Test Quick Mode
```
🧪 Running quick test suite...

Environment:
  ✅ Docker running
  ✅ Ports available
  ✅ Virtual environment active

Test Results:
  ✅ test_unified_server (9/9 passed)
  ✅ test_integration (15/15 passed)
  ✅ test_multi_registry (3/3 passed)
  ✅ test_mcp_container (1/1 passed)
  ✅ test_mcp_compliance (5/5 passed)
  ✅ test_slim_mode (1/1 passed)
  ✅ test_smart_defaults (1/1 passed)

Total: 35/35 passed (100.0%)
Duration: 68 seconds

✅ All tests passed!
```

## Best Practices

### Before Every Commit
```bash
# Run quick lint
/lint-and-test quick

# If issues, fix them
/lint-and-test fix

# Review changes
git diff

# Commit
git commit -m "feat: your changes"
```

### Before Every Push
```bash
# Run CI check
/lint-and-test ci

# Must pass - no exceptions!
# If fails, fix issues first

# Optionally run quick tests
/lint-and-test test-quick

# Push
git push
```

### Before Pull Request
```bash
# Run full validation
/lint-and-test test-full

# All tests must pass
# Review test reports
# Fix any failures

# Create PR
```

## Related Skills

- `/schema-generate` - Generate schemas
- `/schema-evolve` - Evolve schemas
- `/migration-plan` - Plan migrations

## Configuration Files

All lint configuration is in `pyproject.toml`:
- **DO NOT MODIFY** lint configurations
- Write code that passes existing rules
- Configurations are project standards

## Notes

- Virtual environment must be activated for testing
- Docker required for all tests
- Lint checks are fast - run frequently
- Always fix lint issues before committing
- CI mode must pass before pushing
- Test reports saved to `tests/reports/`
