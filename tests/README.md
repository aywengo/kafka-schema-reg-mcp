# Kafka Schema Registry Multi-Registry MCP Server

A comprehensive Message Control Protocol (MCP) server that provides tools for interacting with multiple Kafka Schema Registry instances, including advanced schema management, cross-registry comparison, migration, synchronization, and all original single-registry operations.

## Features

- **48 MCP Tools** total (20 original + 28 new multi-registry tools)
- **Multi-Registry Support**: Connect to multiple Schema Registry instances
- **Cross-Registry Comparison**: Compare schemas, contexts, and entire registries
- **Schema Migration**: Move schemas between registries with conflict detection
- **Synchronization**: Keep registries in sync with scheduled operations
- **Export/Import**: Advanced bulk operations for data migration
- **READONLY Mode**: Production safety for all registries
- **Backward Compatibility**: All existing tools work with optional registry parameter
- **Async Task Queue**: Background processing for long-running operations

## Architecture

### Multi-Registry Configuration

The server supports up to 8 Schema Registry instances through numbered environment variables:

```bash
# Registry 1 (DEV)
SCHEMA_REGISTRY_NAME_1=dev
SCHEMA_REGISTRY_URL_1=http://localhost:38081
SCHEMA_REGISTRY_USER_1=admin
SCHEMA_REGISTRY_PASSWORD_1=admin
READONLY_1=false

# Registry 2 (PROD)
SCHEMA_REGISTRY_NAME_2=prod
SCHEMA_REGISTRY_URL_2=http://localhost:38082
SCHEMA_REGISTRY_USER_2=admin
SCHEMA_REGISTRY_PASSWORD_2=admin
READONLY_2=true
```

### Async Task Management

Long-running operations are managed through an async task queue:

```python
# Task Types
- MIGRATION: Schema migration between registries
- SYNC: Registry synchronization
- CLEANUP: Batch cleanup operations
- EXPORT: Schema export operations
- IMPORT: Schema import operations

# Task States
- PENDING: Task created, waiting to start
- RUNNING: Task currently executing
- COMPLETED: Task finished successfully
- FAILED: Task encountered an error
- CANCELLED: Task was cancelled
```

### Migration Flow

The enhanced migration process includes:

1. **Initial Comparison**
   - Get schemas from both registries
   - Compare schemas and detect collisions

2. **Migration Configuration**
   - For context migrations: Use `migrate_context` to generate Docker configuration
   - For individual schemas: Use `migrate_schema` for direct migration
   - Validate ENABLE_MIGRATION flag

3. **Docker-Based Context Migration** (NEW)
   - Generate `.env` file with registry credentials
   - Create `docker-compose.yml` for the migration container
   - Generate `migrate-context.sh` execution script
   - Review configuration before execution

4. **Mode Setup** (for direct schema migration)
   - Set global IMPORT mode if needed
   - Handle READONLY mode restrictions

5. **Migration Execution**
   - For contexts: Run the Docker-based migrator
   - For schemas: Process each version in order
   - Handle compatibility issues

6. **Post-Migration**
   - Validate migration results
   - Monitor logs in `./logs` directory
   - Restore original registry mode

### Context Migration with Docker

The `migrate_context` function now generates configuration files for the [kafka-schema-reg-migrator](https://github.com/aywengo/kafka-schema-reg-migrator) Docker tool:

```python
# Generate migration configuration
result = migrate_context(
    context="development",
    source_registry="dev",
    target_registry="prod",
    target_context="production",
    preserve_ids=True,
    dry_run=True
)

# Save generated files
with open('.env', 'w') as f:
    f.write(result['files_to_create']['.env']['content'])
    
# Run migration
# ./migrate-context.sh
```

This approach provides:
- Better error handling and recovery
- Scalable bulk migrations
- Progress monitoring and logging
- Configuration review before execution

### ID Preservation

Schema ID preservation is handled through IMPORT mode:

1. **Empty Subject Check**
   - Verify subject is empty/non-existent
   - Set IMPORT mode for all versions

2. **Version Processing**
   - Register schemas with original IDs
   - Maintain version order
   - Handle compatibility issues

3. **Mode Restoration**
   - Restore original registry mode
   - Clean up temporary settings

## Quick Start

### Single Registry Testing
```bash
cd tests/

# Start single registry environment
./start_test_environment.sh

# Run comprehensive tests
./run_comprehensive_tests.sh

# Stop environment
./stop_test_environment.sh
```

### Multi-Registry Testing (Recommended)
```bash
cd tests/

# Start multi-registry environment (DEV + PROD)
./start_multi_registry_environment.sh

# Run all multi-registry tests
./run_multi_registry_tests.sh

# Run migration and comparison tests
./run_migration_tests.sh

# Stop multi-registry environment
./stop_multi_registry_environment.sh
```

## Test Environments

### Single Registry Environment
- **Kafka** on `localhost:9092`
- **Schema Registry** on `localhost:38081`
- **Docker Compose** configuration: `docker-compose.test.yml`
- **Health checks** and automatic startup verification

### Multi-Registry Environment (Production-Ready)
- **Kafka DEV** on `localhost:39092` (external), `9092` (internal)
- **Kafka PROD** on `localhost:39093` (external), `9093` (internal)
- **Schema Registry DEV** on `localhost:38081` (read-write, backward compatibility)
- **Schema Registry PROD** on `localhost:38082` (read-only, forward compatibility)
- **AKHQ UI** on `http://localhost:38080` (manages both clusters)
- **MCP Server** with multi-registry configuration
- **Docker Compose** configuration: `docker-compose.multi-test.yml`

## Test Categories

### Comprehensive Test Suite
Run the complete test suite with:
```bash
./run_comprehensive_tests.sh
```

### Multi-Registry Test Suite

The **comprehensive multi-registry test runner** orchestrates all tests specifically designed for multi-registry environments:

```bash
# Run all multi-registry tests (comprehensive)
./run_multi_registry_tests.sh

# Show usage and options
./run_multi_registry_tests.sh --help

# Run essential tests only
./run_multi_registry_tests.sh --quick
```

**Test Categories:**
1. **Multi-Registry Configuration** - Numbered environment variable setup
2. **Migration Integration** - End-to-end migration functionality 
3. **Default Context '.' Migration** - Fixes the "0 subjects migrated" bug
4. **All Versions Migration** - Complete schema evolution preservation
5. **ID Preservation Migration** - Schema ID preservation using IMPORT mode
6. **End-to-End Workflows** - Complete business workflow scenarios
7. **Error Handling** - Multi-registry error scenarios and edge cases
8. **Performance & Load** - Multi-registry performance validation

## Test Files Overview

### Core Integration Tests
- `test_end_to_end_workflows.py` - Complete business workflow testing
- `test_error_handling.py` - Error conditions and edge cases
- `test_performance_load.py` - Performance and scalability testing
- `test_production_readiness.py` - Enterprise production features
- `test_all_tools_validation.py` - All 68 MCP tools validation

### Multi-Registry Tests
- `test_multi_registry_mcp.py` - Multi-registry functionality validation
- `test_schema_migration.py` - Schema migration from DEV to PROD
- `test_compatibility_migration.py` - Compatibility validation during migration
- `test_bulk_migration.py` - Bulk schema migration across registries
- `test_version_migration.py` - Specific version migration
- `test_registry_comparison.py` - Full registry comparison DEV vs PROD
- `test_schema_drift.py` - Schema drift detection between registries
- `test_readonly_validation.py` - PROD registry read-only enforcement

### Configuration Tests
- `test_simple_config.py` - Single registry configuration
- `test_numbered_config.py` - Multi-registry numbered configuration
- `test_config.py` - Flexible test configuration with auto-detection
- `test_default_context_dot_migration.py` - Default context '.' migration bug fix validation

### Infrastructure Tests
- `test_mcp_server.py` - Basic MCP server functionality
- `test_docker_mcp.py` - Docker integration testing
- `test_integration_setup.py` - Test setup and teardown
- `test_migration_implementation.py` - Migration implementation validation

## Test Infrastructure

### Production Scripts

**Environment Management:**
- `start_multi_registry_environment.sh` - Start multi-registry environment (DEV + PROD)
- `stop_multi_registry_environment.sh` - Stop multi-registry environment
- `start_test_environment.sh` - Start single registry Docker environment
- `stop_test_environment.sh` - Stop single registry environment

**Test Runners:**
- `run_comprehensive_tests.sh` - Main test runner with reporting (single registry)
- `run_multi_registry_tests.sh` - Multi-registry test runner with all categories
- `run_migration_tests.sh` - Schema migration and comparison tests
- `run_default_context_dot_tests.sh` - Default context '.' migration bug fix tests

**Utilities:**
- `cleanup_multi_registry.sh` - Complete cleanup for multi-registry environment
- `cleanup_containers.sh` - Quick cleanup for Docker conflicts
- `restart_schema_registry.sh` - Restart just Schema Registry (troubleshooting)
- `test_docker_image.sh` - Docker image validation testing

### Configuration Files

**Docker Environments:**
- `docker-compose.test.yml` - Single registry environment
- `docker-compose.multi-test.yml` - Multi-registry environment (DEV + PROD)
- `docker-compose.simple.yml` - Simplified single registry (fallback option)

**Test Configuration:**
- `test_config.py` - Flexible test configuration with auto-detection

## Environment Variables

### Single Registry Testing
```bash
export SCHEMA_REGISTRY_URL="http://localhost:38081"
export SCHEMA_REGISTRY_USER="username"
export SCHEMA_REGISTRY_PASSWORD="password"
export READONLY="false"
```

### Multi-Registry Testing (Numbered Configuration)
```bash
# Registry 1 (Development)
export SCHEMA_REGISTRY_NAME_1="development"
export SCHEMA_REGISTRY_URL_1="http://localhost:38081"
export READONLY_1="false"

# Registry 2 (Production)
export SCHEMA_REGISTRY_NAME_2="production"
export SCHEMA_REGISTRY_URL_2="http://localhost:38082"
export READONLY_2="true"

# Registry 3 (Staging - optional)
export SCHEMA_REGISTRY_NAME_3="staging"
export SCHEMA_REGISTRY_URL_3="http://localhost:38083"
export READONLY_3="false"
```

## Port Configuration

### Multi-Registry Environment
- **AKHQ UI**: `http://localhost:38080`
- **DEV Registry**: `http://localhost:38081` (read-write)
- **PROD Registry**: `http://localhost:38082` (read-only)
- **Kafka DEV**: `localhost:39092` (external), `9092` (internal)
- **Kafka PROD**: `localhost:39093` (external), `9093` (internal)

### Single Registry Environment
- **Schema Registry**: `http://localhost:38081`
- **Kafka**: `localhost:9092`

## Running Individual Tests

```bash
# Run a specific test file
python3 test_end_to_end_workflows.py

# Run migration tests individually
python3 test_schema_migration.py
python3 test_registry_comparison.py
python3 test_readonly_validation.py

# Run with pytest for more options
pytest test_performance_load.py -v

# Run specific test categories with pytest
pytest -k "test_schema_evolution" -v
```

## Prerequisites

### Required Software
- **Docker Desktop** - For running Kafka and Schema Registry
- **Python 3.8+** - With virtual environment recommended
- **curl** - For health checks and manual testing

### Python Dependencies
```bash
# Install dependencies (from project root)
pip install -r requirements.txt
```

Required packages:
- `mcp` - MCP client library
- `asyncio` - Async programming support
- `requests` - HTTP client
- `pytest` - Testing framework
- `aiofiles` - Async file operations

## Troubleshooting

### Multi-Registry Environment Issues
```bash
# Check all services status
docker-compose -f docker-compose.multi-test.yml ps

# View logs for specific service
docker logs kafka-dev
docker logs kafka-prod
docker logs schema-registry-dev
docker logs schema-registry-prod
docker logs akhq-multi

# Complete cleanup and restart
./cleanup_multi_registry.sh
./start_multi_registry_environment.sh
```

### Single Registry Issues
```bash
# Check Docker status
docker ps | grep -E 'kafka-test|schema-registry-test'

# View logs
docker logs kafka-test
docker logs schema-registry-test

# Clean restart environment
./cleanup_containers.sh
./start_test_environment.sh
```

### Schema Registry Startup Issues
If Schema Registry fails to start within the timeout:

```bash
# 1. Check specific logs
docker logs schema-registry-dev --tail 20
docker logs schema-registry-prod --tail 20

# 2. Manual verification
curl http://localhost:38081/subjects
curl http://localhost:38082/subjects

# 3. Try single registry for testing
./start_test_environment.sh
```

Common Schema Registry issues:
- **Still initializing**: Wait 2-3 minutes for first startup
- **Kafka connection**: Ensure Kafka is fully ready before Schema Registry starts
- **Port conflicts**: Check if ports 38080-38082 are already in use
- **Docker resources**: Ensure Docker has sufficient memory (4GB+ recommended)

### Port Conflicts
```bash
# Check what's using the ports
lsof -i :38080  # AKHQ UI
lsof -i :38081  # DEV Registry
lsof -i :38082  # PROD Registry

# Kill conflicting processes if needed
sudo lsof -ti:38081 | xargs kill -9
```

### Test Failures
```bash
# Check detailed logs
ls -la results/
cat results/test_summary_*.txt
cat results/multi_registry_summary_*.txt
cat results/migration_summary_*.txt

# Run with verbose output
./run_comprehensive_tests.sh --basic 2>&1 | tee debug.log

# Check Python environment
python3 -c "import mcp, asyncio, requests; print('Dependencies OK')"

# Validate migration implementation
python3 test_migration_implementation.py
```

## Test Results

After running tests, results are available in:
- `results/test_summary_TIMESTAMP.txt` - Comprehensive test summary
- `results/multi_registry_summary_TIMESTAMP.txt` - Multi-registry test summary  
- `results/migration_summary_TIMESTAMP.txt` - Migration test summary
- `results/test_results_TIMESTAMP.csv` - Machine-readable results
- `results/comprehensive_test_TIMESTAMP.log` - Detailed execution log
- `results/TESTNAME_TIMESTAMP.log` - Individual test logs

## Performance Metrics

The test suite includes comprehensive performance validation:
- **Schema Registration**: Measures throughput for bulk operations
- **Cross-Registry Operations**: Tests latency for multi-registry workflows
- **Migration Performance**: Bulk migration timing and success rates
- **Concurrent Operations**: Validates performance under load
- **Memory Usage**: Monitors resource consumption
- **Response Times**: P95 latency measurements
- **Read-Only Performance**: PROD registry read operation benchmarks

## Migration and Comparison Features

The test suite validates advanced multi-registry features:
- **Schema Migration**: DEV → PROD migration workflows
- **Registry Comparison**: Full registry comparison and diff analysis
- **Compatibility Validation**: Schema evolution compatibility checking
- **Drift Detection**: Automated schema drift detection between registries
- **Bulk Operations**: Batch migration and comparison operations
- **Version Management**: Specific version migration and tracking
- **Read-Only Enforcement**: PROD registry protection validation

## Integration with CI/CD

The test suite is designed for CI/CD integration:
```bash
# Non-interactive execution
export CI=true
./start_multi_registry_environment.sh
./run_multi_registry_tests.sh
exit_code=$?
./stop_multi_registry_environment.sh
exit $exit_code
```

## Contributing

When adding new tests:
1. Follow the naming convention: `test_*.py`
2. Include docstrings and error handling
3. Add to appropriate category in test runners
4. Test both single and multi-registry scenarios where applicable
5. Include performance metrics where applicable
6. Update this README with new test descriptions
7. Ensure proper port configuration (38080, 38081, 38082)
8. Test cleanup and resource management 