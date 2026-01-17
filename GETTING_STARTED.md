# Getting Started - Contributing to Kafka Schema Registry MCP

Welcome! This guide will help you get up and running with contributing to the Kafka Schema Registry MCP Server project.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Setup](#quick-setup)
3. [Claude Code Skills](#claude-code-skills)
4. [Development Workflow](#development-workflow)
5. [Running Tests](#running-tests)
6. [Code Quality](#code-quality)
7. [Making Changes](#making-changes)
8. [Submitting Changes](#submitting-changes)
9. [Common Tasks](#common-tasks)
10. [Troubleshooting](#troubleshooting)
11. [Resources](#resources)

---

## Prerequisites

Before you begin, ensure you have the following installed:

### Required

- **Python 3.10+** (project requires 3.10, CI uses 3.11)
  ```bash
  python3 --version  # Should show 3.10.0 or higher
  ```

- **Docker Desktop** (for running tests)
  ```bash
  docker --version
  docker ps  # Verify Docker is running
  ```

- **Git**
  ```bash
  git --version
  ```

### System Requirements

- **Available Ports**: 38080, 38081, 38082, 9092, 39093
- **Docker Memory**: At least 4GB allocated to Docker Desktop
- **Disk Space**: ~2GB for dependencies and Docker images

---

## Quick Setup

### 1. Clone the Repository

```bash
# Clone the main repository
git clone https://github.com/aywengo/kafka-schema-reg-mcp.git
cd kafka-schema-reg-mcp

# Or if you already have it, navigate to it
cd /path/to/kafka-schema-reg-mcp
```

### 2. Create a Branch

```bash
# Create and checkout a new branch for your work
git checkout -b feature/your-feature-name

# Or use a worktree (recommended for working on multiple features)
git worktree add ~/.claude-worktrees/kafka-schema-reg-mcp/your-branch-name -b your-branch-name
cd ~/.claude-worktrees/kafka-schema-reg-mcp/your-branch-name
```

### 3. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate  # On Windows

# Upgrade pip
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt

# Install development dependencies
pip install black flake8 isort mypy ruff pytest-asyncio
```

### 4. Verify Setup

```bash
# Run quick lint check
./scripts/quick-lint-check.sh

# Check all tools are installed
black --version
flake8 --version
isort --version
ruff --version
```

**Expected output:**
```
✅ All critical checks passed! Ready for CI.
```

---

## Claude Code Skills

This project includes **4 specialized Claude Code skills** to automate common development tasks and boost productivity.

### Available Skills

#### 1. `/schema-generate` - Generate Schemas
Generate production-ready Avro schemas from natural language descriptions.

```
/schema-generate event UserRegistered "user registration with userId, email, registrationMethod enum, timestamp"

/schema-generate entity Product "product with id, name, price, inventory, status"
```

**Use when:** Starting a new schema from scratch

---

#### 2. `/schema-evolve` - Evolve Schemas
Safely evolve existing schemas with automatic compatibility checking.

```
/schema-evolve user-profile "add optional phoneNumber and preferences fields"

/schema-evolve order-event "add REFUNDED enum value to orderStatus"
```

**Use when:** Modifying existing schemas while maintaining compatibility

---

#### 3. `/migration-plan` - Plan Migrations
Generate comprehensive migration plans for promoting schemas between environments.

```
/migration-plan development staging

/migration-plan staging production --with-rollback
```

**Use when:** Deploying schemas from dev → staging → production

---

#### 4. `/lint-and-test` - Quality Automation
Run linting and testing workflows with auto-fix capabilities.

```
/lint-and-test quick        # Before commit (2-3 seconds)
/lint-and-test fix          # Auto-fix formatting issues
/lint-and-test pre-commit   # Pre-commit workflow
/lint-and-test pre-push     # Pre-push workflow
```

**Use when:** Before every commit and push

---

### Quick Skills Tutorial

**5-Minute Quick Start:** Read [`.claude-code/SKILLS_GUIDE.md`](.claude-code/SKILLS_GUIDE.md)

**Complete Reference:** [`.claude-code/skills/README.md`](.claude-code/skills/README.md)

**Setup Documentation:** [`CLAUDE_CODE_SKILLS_SETUP.md`](CLAUDE_CODE_SKILLS_SETUP.md)

### Skills in Daily Workflow

```bash
# Morning
source .venv/bin/activate
/lint-and-test quick

# During development
/schema-generate event OrderPlaced "order with id, items, total"
/schema-evolve user-profile "add loyalty points"
/lint-and-test quick

# Before commit
/lint-and-test pre-commit
git commit -m "feat: add order schema"

# Before push
/lint-and-test pre-push
git push
```

---

## Development Workflow

### Standard Development Cycle

```bash
# 1. Activate virtual environment (if not already active)
source .venv/bin/activate

# 2. Make your code changes
# Edit files in your favorite editor

# 3. Run quick lint check frequently
./scripts/quick-lint-check.sh

# 4. Auto-fix formatting issues
./scripts/check-lint-issues.sh --fix

# 5. Review your changes
git status
git diff

# 6. Run tests (if applicable)
cd tests && ./run_all_tests.sh --quick

# 7. Commit your changes
git add .
git commit -m "feat: add new feature description"

# 8. Before pushing, run CI check
./scripts/ci-lint-check.sh

# 9. Push your changes
git push origin your-branch-name
```

---

## Running Tests

### Prerequisites for Tests

1. **Docker Desktop must be running**
2. **Ports must be available**: 38080-38082, 9092, 39093
3. **Sufficient Docker memory**: 4GB+ recommended

### Test Commands

```bash
# Quick tests (essential tests only, ~2-5 minutes)
cd tests
./run_all_tests.sh --quick

# Full test suite (comprehensive, ~10-15 minutes)
cd tests
./run_all_tests.sh

# Keep test environment running for debugging
cd tests
./run_all_tests.sh --no-cleanup

# Run specific test categories
./run_comprehensive_tests.sh --category performance
./run_comprehensive_tests.sh --category production

# Migration tests
./run_migration_integration_tests.sh
```

### Understanding Test Output

- ✅ **Green/PASS**: Tests passed successfully
- ❌ **Red/FAIL**: Tests failed (review error messages)
- ⚠️ **Yellow/WARN**: Warnings (may not fail CI)

**Test Reports:** Generated in `tests/reports/`

---

## Code Quality

### Linting Tools

The project uses multiple linting tools with specific configurations:

| Tool | Purpose | Line Length | Config File |
|------|---------|-------------|-------------|
| **Black** | Code formatting | 120 | `pyproject.toml` |
| **isort** | Import sorting | 120 | `pyproject.toml` |
| **Ruff** | Fast Python linter | 120 | `pyproject.toml` |
| **Flake8** | Style checking | 127 | `pyproject.toml` |
| **MyPy** | Type checking (optional) | - | `pyproject.toml` |

### Pre-Commit Checklist

**Always run these before committing:**

```bash
# 1. Quick check (2-3 seconds) - REQUIRED
./scripts/quick-lint-check.sh

# 2. If quick check fails, run comprehensive check with auto-fix
./scripts/check-lint-issues.sh --fix

# 3. Review what was changed
git diff
```

### Pre-Push Checklist

**Before pushing to remote:**

```bash
# 1. Run CI mirror check (10-15 seconds) - REQUIRED
./scripts/ci-lint-check.sh

# 2. Optionally run quick tests
cd tests && ./run_all_tests.sh --quick
```

### Auto-Fixing Issues

```bash
# Auto-fix formatting with Black and isort
./scripts/check-lint-issues.sh --fix

# Or manually
source .venv/bin/activate
black *.py tests/*.py
isort *.py tests/*.py
```

---

## Making Changes

### Project Structure

```
kafka-schema-reg-mcp/
├── .claude-code/           # Claude Code configuration (new!)
│   ├── config.json         # Project configuration
│   ├── workspace.json      # Workspace settings
│   └── templates/          # Schema templates
├── docs/                   # Documentation
├── tests/                  # Test suite
├── scripts/                # Utility scripts
├── config-examples/        # Example configurations
├── *.py                    # Main Python modules (24 files)
├── pyproject.toml          # Project configuration
├── requirements.txt        # Dependencies
├── AGENTS.md              # Development guidelines
└── GETTING_STARTED.md     # This file!
```

### Key Files to Know

- **`AGENTS.md`** - Development guidelines and pre-commit checklist
- **`pyproject.toml`** - Linting and project configuration (DO NOT MODIFY)
- **`requirements.txt`** - Python dependencies
- **`TESTING_SETUP_GUIDE.md`** - Comprehensive testing documentation
- **`CHANGELOG.md`** - Version history and changes

### Making Code Changes

1. **Read existing code** before modifying
2. **Follow existing patterns** and conventions
3. **Add tests** for new features
4. **Update documentation** if needed
5. **Run lint checks** frequently

### Commit Message Format

Follow conventional commits:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `chore:` - Maintenance tasks
- `refactor:` - Code refactoring
- `perf:` - Performance improvements

**Examples:**
```bash
git commit -m "feat: add schema migration with rollback support"
git commit -m "fix: resolve compatibility check for AVRO schemas"
git commit -m "docs: update API reference for new endpoints"
git commit -m "test: add integration tests for multi-registry"
```

---

## Submitting Changes

### Creating a Pull Request

1. **Ensure all checks pass**
   ```bash
   ./scripts/ci-lint-check.sh
   cd tests && ./run_all_tests.sh --quick
   ```

2. **Push your branch**
   ```bash
   git push origin your-branch-name
   ```

3. **Create PR on GitHub**
   - Go to https://github.com/aywengo/kafka-schema-reg-mcp
   - Click "New Pull Request"
   - Select your branch
   - Fill in PR template with:
     - Description of changes
     - Related issues (if any)
     - Testing performed
     - Screenshots (if UI changes)

4. **Wait for CI checks**
   - GitHub Actions will run automatically
   - All checks must pass before merge
   - Address any failing checks

5. **Respond to review comments**
   - Make requested changes
   - Push updates to same branch
   - Re-request review when ready

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] All lint checks pass (`./scripts/ci-lint-check.sh`)
- [ ] Tests pass locally (`./run_all_tests.sh --quick`)
- [ ] New tests added for new features
- [ ] Documentation updated (if needed)
- [ ] CHANGELOG.md updated (if needed)
- [ ] Commit messages follow conventional format
- [ ] No merge conflicts with main branch

---

## Common Tasks

### Running the MCP Server Locally

```bash
# Single registry mode
source .venv/bin/activate
export SCHEMA_REGISTRY_URL=http://localhost:8081
python kafka_schema_registry_unified_mcp.py

# Multi-registry mode
export MULTI_REGISTRY_CONFIG=multi_registry.env
python remote-mcp-server.py
```

### Running with Docker

```bash
# Build Docker image
docker build -t kafka-schema-reg-mcp:dev .

# Run container
docker run -d \
  -p 38000:38000 \
  -e SCHEMA_REGISTRY_URL=http://host.docker.internal:8081 \
  kafka-schema-reg-mcp:dev
```

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart specific service
docker-compose restart mcp-server
```

### Generating Documentation

```bash
# Export schemas as documentation
curl -X POST http://localhost:38000/export/global \
  -H 'Content-Type: application/json' \
  -d '{"format": "bundle", "include_metadata": true}' \
  --output docs/schemas_$(date +%Y%m%d).zip
```

### Testing Schema Registration

```bash
# Register a test schema
curl -X POST http://localhost:38000/schemas \
  -H 'Content-Type: application/json' \
  -d '{
    "subject": "test-user",
    "schema": {
      "type": "record",
      "name": "User",
      "fields": [
        {"name": "id", "type": "string"},
        {"name": "name", "type": "string"}
      ]
    },
    "schemaType": "AVRO",
    "context": "development"
  }'
```

---

## Troubleshooting

### Common Issues

#### 1. Import Errors

**Problem:** `ModuleNotFoundError` or import errors

**Solution:**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Add current directory to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### 2. Docker Errors

**Problem:** Tests fail with Docker connection errors

**Solution:**
```bash
# Check Docker is running
docker ps

# Restart Docker Desktop
# Verify ports are available
for port in 38080 38081 38082 9092 39093; do
  nc -z localhost $port && echo "Port $port in use" || echo "Port $port available"
done

# Clean up Docker
docker-compose down -v
docker system prune -f
```

#### 3. Lint Check Failures

**Problem:** Lint checks fail with formatting errors

**Solution:**
```bash
# Auto-fix most issues
./scripts/check-lint-issues.sh --fix

# Check what will be changed
git diff

# Manually fix remaining issues
source .venv/bin/activate
black *.py
isort *.py
```

#### 4. Test Failures

**Problem:** Tests fail locally but CI is unclear

**Solution:**
```bash
# Run tests with verbose output
cd tests
./run_all_tests.sh --quick --verbose

# Keep environment running for debugging
./run_all_tests.sh --no-cleanup

# Check service health
docker-compose ps
docker-compose logs mcp-server
```

#### 5. Port Already in Use

**Problem:** `Port 38080 already in use`

**Solution:**
```bash
# Find process using port
lsof -i :38080

# Kill process (replace PID)
kill -9 <PID>

# Or use different ports in .env
export MCP_SERVER_PORT=39000
```

### Getting Help

- **Documentation**: Check `docs/` directory
- **Development Guide**: See `AGENTS.md`
- **Testing Guide**: See `TESTING_SETUP_GUIDE.md`
- **GitHub Issues**: https://github.com/aywengo/kafka-schema-reg-mcp/issues
- **API Reference**: `docs/api-reference.md`

---

## Resources

### Documentation

- **README.md** - Project overview and features
- **AGENTS.md** - Development guidelines and pre-commit checklist
- **TESTING_SETUP_GUIDE.md** - Comprehensive testing documentation
- **docs/api-reference.md** - Complete API documentation
- **docs/deployment.md** - Deployment guides (Docker, Kubernetes, Cloud)
- **docs/ide-integration.md** - IDE setup (VS Code, Claude Code, Cursor)
- **CHANGELOG.md** - Version history

### Claude Code Skills Documentation

- **`.claude-code/SKILLS_GUIDE.md`** - 5-minute quick start tutorial ⭐
- **`.claude-code/skills/README.md`** - Complete skills reference
- **`.claude-code/skills/schema-generate.md`** - Schema generation skill
- **`.claude-code/skills/schema-evolve.md`** - Schema evolution skill
- **`.claude-code/skills/migration-plan.md`** - Migration planning skill
- **`.claude-code/skills/lint-and-test.md`** - Quality assurance skill

### Configuration Examples

Located in `config-examples/`:
- Claude Desktop configurations (25+ examples)
- Docker configurations
- Multi-registry setups
- OAuth provider configurations
- SLIM_MODE examples

### Scripts

Located in `scripts/`:
- `quick-lint-check.sh` - Quick pre-commit check (~2-3s)
- `check-lint-issues.sh` - Comprehensive check with auto-fix (~20-30s)
- `ci-lint-check.sh` - CI mirror check (~10-15s)

### Tests

Located in `tests/`:
- `run_all_tests.sh` - Main test runner
- `run_migration_integration_tests.sh` - Migration tests
- `run_comprehensive_tests.sh` - Category-based testing
- 80+ test files covering all features

### Claude Code

Located in `.claude-code/`:
- `config.json` - Project configuration
- `workspace.json` - Workspace settings
- `templates/` - Schema templates (Event, Entity, Command, Aggregate)
- `skills/` - Claude Code skills (4 specialized skills)
- `SKILLS_GUIDE.md` - Quick start guide for skills ⭐
- `README.md` - Claude Code usage guide

---

## Next Steps

1. ✅ **Complete the setup** - Follow Quick Setup section
2. 🛠️ **Try Claude Code Skills** - Read `.claude-code/SKILLS_GUIDE.md` (5 minutes)
3. 📖 **Read AGENTS.md** - Understand development workflow
4. 🧪 **Run tests** - Familiarize yourself with test suite
5. 💻 **Make a small change** - Use `/schema-generate` to create a test schema
6. 🔍 **Review a PR** - Learn from existing contributions
7. 🚀 **Start contributing** - Pick an issue or suggest improvements

---

## Welcome to the Team!

Thank you for contributing to Kafka Schema Registry MCP! Your contributions help make schema management better for everyone.

**Happy coding! 🎉**

---

**Version:** 2.1.5
**Last Updated:** 2026-01-17
**Maintainer:** @aywengo
