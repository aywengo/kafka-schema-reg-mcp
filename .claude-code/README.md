# Claude Code Configuration

This directory contains custom configuration and templates for working with the Kafka Schema Registry MCP project using Claude Code.

## Files

### Configuration Files

- **`config.json`** - Main Claude Code project configuration
  - MCP server definitions
  - Development environment settings
  - Linting and testing configurations
  - AI assistance settings
  - Workflow definitions

- **`workspace.json`** - Workspace-specific settings
  - AI-enhanced features configuration
  - Code quality settings
  - File watchers and automation
  - Smart features and hints

### Templates

The `templates/` directory contains Avro schema templates for common patterns:

- **`event-schema.json`** - Domain event schema template
  - Standard event metadata (eventId, eventType, timestamp, version)
  - Event source tracking
  - Extensible metadata support

- **`entity-schema.json`** - Business entity schema template
  - Entity lifecycle fields (id, version, createdAt, updatedAt)
  - Status tracking
  - Audit fields (createdBy, updatedBy)

- **`command-schema.json`** - CQRS command schema template
  - Command identification and tracking
  - Issuer information
  - Optimistic locking support

- **`aggregate-schema.json`** - DDD aggregate root template
  - Aggregate versioning for event sourcing
  - State snapshots
  - Child entity management

## Quick Start

### 1. Activate Virtual Environment

```bash
source .venv/bin/activate
```

### 2. Run Lint Checks

```bash
# Quick check (2-3 seconds)
./scripts/quick-lint-check.sh

# Comprehensive check with auto-fix
./scripts/check-lint-issues.sh --fix

# CI mirror check (before pushing)
./scripts/ci-lint-check.sh
```

### 3. Run Tests

```bash
# Quick tests (essential only)
cd tests && ./run_all_tests.sh --quick

# Full test suite
cd tests && ./run_all_tests.sh

# Keep environment running for debugging
cd tests && ./run_all_tests.sh --no-cleanup
```

## AI-Enhanced Workflows

### Schema Generation

Use natural language to generate schemas:

```
Generate an event schema for user registration with fields:
- userId (required)
- email (required)
- registrationMethod (enum: EMAIL, GOOGLE, FACEBOOK)
- registrationTimestamp
```

### Schema Evolution

Evolve existing schemas with compatibility checking:

```
Evolve the user-profile schema to add:
- socialLoginProvider field
- privacyPreferences record
While maintaining backward compatibility
```

### Migration Planning

Create migration plans between contexts:

```
Plan migration from development to staging:
- Analyze compatibility
- Generate migration sequence
- Create rollback plan
```

## Shortcuts

Configured shortcuts for common tasks:

- `schema:analyze` - Analyze schema and provide recommendations
- `schema:generate` - Generate schema from description
- `schema:evolve` - Evolve schema with compatibility checking
- `migration:plan` - Generate migration plan
- `migration:execute` - Execute migration with monitoring
- `export:smart` - AI-optimized export strategy
- `docs:generate` - Generate documentation
- `lint:check` - Quick lint check
- `lint:fix` - Comprehensive lint with auto-fix
- `test:quick` - Quick test suite
- `test:full` - Full test suite

## Development Contexts

Available schema contexts:

- `development` - For active development and experimentation
- `staging` - For pre-production testing
- `production` - Production schemas (read-only recommended)
- `testing` - For automated testing

## Linting Configuration

All linting is configured in `pyproject.toml`:

- **Black**: Line length 120
- **Ruff**: Line length 120, max complexity 15
- **isort**: Profile black, line length 120
- **Flake8**: Max line length 127, max complexity 15
- **MyPy**: Optional, not enforced in CI

**Important**: Never modify lint configurations in `pyproject.toml`. Write code that passes existing rules.

## Testing Requirements

- Docker Desktop must be running
- Ports available: 38080-38082, 9092, 39093
- At least 4GB RAM allocated to Docker

## Important Notes

1. Always run lint checks before committing
2. Use virtual environment for all Python operations
3. Docker required for running tests
4. Never modify `pyproject.toml` lint configurations
5. Run `./scripts/ci-lint-check.sh` before pushing

## Documentation

- **Main docs**: `docs/`
- **API Reference**: `docs/api-reference.md`
- **Testing Guide**: `TESTING_SETUP_GUIDE.md`
- **Development Guide**: `AGENTS.md`
- **Integration Guide**: `docs/ide-integration.md`

## Support

For issues or questions:
- Check `AGENTS.md` for development guidelines
- Review `TESTING_SETUP_GUIDE.md` for testing help
- See `docs/ide-integration.md` for IDE setup

## Version

Configuration version: 2.1.5
Last updated: 2026-01-17
