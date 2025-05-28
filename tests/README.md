# Integration Tests for Kafka Schema Registry MCP Server

This directory contains comprehensive integration tests for the multi-registry Kafka Schema Registry MCP server, along with all the infrastructure needed to run them.

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

### Docker Setup

**Single Registry** (`docker-compose.test.yml`):
- `kafka-test`: Confluent Kafka 7.5.0 in KRaft mode
- `schema-registry-test`: Confluent Schema Registry 7.5.0

**Multi-Registry** (`docker-compose.multi-test.yml`):
- `kafka-dev` + `kafka-prod`: Two Kafka clusters with distinct configurations
- `schema-registry-dev` + `schema-registry-prod`: Two Schema Registry instances
- `akhq-multi`: AKHQ UI for both clusters
- `mcp-server-multi`: MCP server with numbered configuration

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

# Run essential tests only (future feature)
./run_multi_registry_tests.sh --quick
```

**Features:**
- **Automatic Environment Detection**: Validates DEV + PROD registries are healthy
- **8 Test Categories**: Covers all multi-registry functionality
- **Comprehensive Reporting**: Detailed success/failure analysis
- **Duration Tracking**: Performance metrics for each test category
- **Production Safety**: Validates production-ready configurations

**Test Categories Executed:**
1. **Multi-Registry Configuration** - Numbered environment variable setup
2. **Migration Integration** - End-to-end migration functionality 
3. **Default Context '.' Migration** - Fixes the "0 subjects migrated" bug
4. **All Versions Migration** - Complete schema evolution preservation
5. **ID Preservation Migration** - Schema ID preservation using IMPORT mode
6. **End-to-End Workflows** - Complete business workflow scenarios
7. **Error Handling** - Multi-registry error scenarios and edge cases
8. **Performance & Load** - Multi-registry performance validation

**Prerequisites:**
- Multi-registry environment on ports 38081-38082
- Start with: `./start_multi_registry_environment.sh`

**Sample Output:**
```
🚀 Kafka Schema Registry Multi-Registry Test Suite
==================================================
✅ DEV Registry at http://localhost:38081 is healthy
✅ PROD Registry at http://localhost:38082 is healthy
🎉 Multi-registry environment is ready!

🚀 Running Multi-Registry Test Suite
Total test categories: 8

======================================
 Running: Multi-Registry Configuration
======================================
✅ Multi-Registry Configuration PASSED (45s)

======================================
 Running: Migration Integration  
======================================
✅ Migration Integration PASSED (73s)

...

🎉 ALL MULTI-REGISTRY TESTS PASSED!
✅ Multi-registry configuration works correctly
✅ Cross-registry operations function properly  
✅ Schema migration preserves data integrity
✅ ID preservation maintains referential integrity
```

### Individual Test Categories

**Comprehensive Tests (Single Registry):**
```bash
# Basic configuration tests
./run_comprehensive_tests.sh --basic

# End-to-end workflow tests
./run_comprehensive_tests.sh --workflows

# Error handling and edge cases
./run_comprehensive_tests.sh --errors

# Performance and load testing
./run_comprehensive_tests.sh --performance

# Production readiness validation
./run_comprehensive_tests.sh --production

# Legacy integration tests
./run_comprehensive_tests.sh --legacy
```

**Multi-Registry Tests:**
```bash
# Multi-registry configuration tests
./run_multi_registry_tests.sh --config

# Cross-registry workflow tests
./run_multi_registry_tests.sh --workflows

# All 68 tools with multi-registry setup
./run_multi_registry_tests.sh --tools

# Multi-registry performance tests
./run_multi_registry_tests.sh --performance

# Migration and comparison tests
./run_multi_registry_tests.sh --migration
```

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

### Legacy Tests
- `test_numbered_integration.py` - Legacy numbered configuration
- `advanced_mcp_test.py` - Advanced MCP features
- `test_unit.py` - Unit tests

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
- `run_integration_tests.sh` - Legacy integration test runner
- `run_numbered_integration_tests.sh` - Numbered config test runner

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
- `pytest.ini` - Pytest configuration

### Results and Documentation
- `results/` - Test execution results, logs, and CSV reports
- `CLEANUP_SUMMARY.md` - Documentation of script cleanup performed
- `MIGRATION_IMPLEMENTATION_SUMMARY.md` - Migration test implementation details
- Generated automatically during test runs with performance metrics

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