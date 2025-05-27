# Testing Setup Guide

This guide provides multiple options for setting up the Schema Registry environment needed to run the comprehensive integration tests.

## Quick Start (Recommended)

### Multi-Registry Environment (Production-Ready)
```bash
# Start the complete multi-registry environment
cd tests
./start_multi_registry_environment.sh

# Run all tests including migration and comparison
./run_multi_registry_tests.sh

# Or run comprehensive tests
./run_comprehensive_tests.sh
```

This sets up:
- **AKHQ UI**: http://localhost:38080
- **DEV Registry**: http://localhost:38081 (read-write)
- **PROD Registry**: http://localhost:38082 (read-only)
- **Kafka DEV**: localhost:39092
- **Kafka PROD**: localhost:39093

## Option 1: Docker Multi-Registry Setup (Recommended)

### Install Docker Desktop
1. Download Docker Desktop for macOS: https://www.docker.com/products/docker-desktop/
2. Install and start Docker Desktop
3. Verify installation: `docker --version`

### Start Multi-Registry Test Environment
```bash
# Start the complete multi-registry environment
cd tests
./start_multi_registry_environment.sh

# Verify all services are running
curl http://localhost:38081/subjects  # DEV Registry
curl http://localhost:38082/subjects  # PROD Registry
curl http://localhost:38080/api/health # AKHQ UI

# Run all tests
./run_multi_registry_tests.sh
```

### Stop Multi-Registry Environment
```bash
cd tests
./stop_multi_registry_environment.sh

# Or complete cleanup
./cleanup_multi_registry.sh
```

## Option 2: Single Registry Docker Setup

For basic testing with a single registry:

```bash
# Start single test Schema Registry on port 38081
cd tests
docker-compose -f docker-compose.test.yml up -d

# Verify it's running
curl http://localhost:38081/subjects

# Run basic tests
./run_comprehensive_tests.sh --basic
```

## Option 3: Use Confluent Cloud

If you have a Confluent Cloud account, you can run tests against a cloud Schema Registry:

```bash
# Set environment variables for your Confluent Cloud instance
export SCHEMA_REGISTRY_URL="https://your-sr-endpoint.us-west-2.aws.confluent.cloud"
export SCHEMA_REGISTRY_USER="your-api-key"
export SCHEMA_REGISTRY_PASSWORD="your-api-secret"

# Run the tests
./run_comprehensive_tests.sh --basic
```

## Option 4: Use Existing Local Schema Registry

If you already have a Schema Registry running locally:

```bash
# If running on port 38081 (default)
./run_comprehensive_tests.sh

# If running on a different port
export SCHEMA_REGISTRY_URL="http://localhost:YOUR_PORT"
./run_comprehensive_tests.sh --basic
```

## Option 5: Custom Multi-Registry Setup

For custom multi-registry testing with your own registries:

```bash
# Registry 1: Development
export SCHEMA_REGISTRY_NAME_1="development"
export SCHEMA_REGISTRY_URL_1="http://localhost:38081"
export READONLY_1="false"

# Registry 2: Staging  
export SCHEMA_REGISTRY_NAME_2="staging"
export SCHEMA_REGISTRY_URL_2="http://localhost:38082"
export READONLY_2="false"

# Registry 3: Production (read-only)
export SCHEMA_REGISTRY_NAME_3="production"
export SCHEMA_REGISTRY_URL_3="http://localhost:38083"
export READONLY_3="true"

# Run multi-registry tests
./run_multi_registry_tests.sh
```

## Test Categories

You can run specific test categories based on your setup:

### Multi-Registry Tests (Full Environment Required)
```bash
# Complete multi-registry test suite
./run_multi_registry_tests.sh

# Migration and comparison tests
./run_migration_tests.sh

# All categories
./run_multi_registry_tests.sh --all
```

### Single Registry Tests
```bash
# Basic functionality tests
./run_comprehensive_tests.sh --basic

# Workflow tests (requires functional Schema Registry)
./run_comprehensive_tests.sh --workflows

# Error handling tests
./run_comprehensive_tests.sh --errors

# Performance tests (generates load)
./run_comprehensive_tests.sh --performance

# Production readiness tests
./run_comprehensive_tests.sh --production
```

## Troubleshooting

### Multi-Registry Environment Issues
```bash
# Check all services status
docker-compose -f tests/docker-compose.multi-test.yml ps

# View logs for specific service
docker logs kafka-dev
docker logs schema-registry-dev
docker logs akhq-multi

# Complete cleanup and restart
cd tests
./cleanup_multi_registry.sh
./start_multi_registry_environment.sh
```

### Schema Registry Not Responding
```bash
# Check if the service is running
curl -f http://localhost:38081/subjects

# Check Docker containers (if using Docker)
docker ps | grep schema-registry

# Check specific registry logs
docker logs schema-registry-dev --tail 20
docker logs schema-registry-prod --tail 20
```

### Port Conflicts
If ports are already in use:

```bash
# Find what's using the ports
lsof -i :38081  # DEV Registry
lsof -i :38082  # PROD Registry
lsof -i :38080  # AKHQ UI

# Kill conflicting processes if needed
sudo lsof -ti:38081 | xargs kill -9
```

### Authentication Issues
```bash
# Test authentication manually
curl -u username:password http://your-registry:38081/subjects

# Verify environment variables
echo $SCHEMA_REGISTRY_USER
echo $SCHEMA_REGISTRY_PASSWORD
```

## Environment Variables Reference

### Single Registry Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `SCHEMA_REGISTRY_URL` | Primary Schema Registry URL | `http://localhost:38081` |
| `SCHEMA_REGISTRY_USER` | Username for authentication | `""` |
| `SCHEMA_REGISTRY_PASSWORD` | Password for authentication | `""` |
| `READONLY` | Read-only mode | `"false"` |

### Multi-Registry Configuration (Numbered)
| Variable | Description | Default |
|----------|-------------|---------|
| `SCHEMA_REGISTRY_NAME_X` | Name for registry X (1-8) | None |
| `SCHEMA_REGISTRY_URL_X` | URL for registry X (1-8) | None |
| `SCHEMA_REGISTRY_USER_X` | User for registry X (1-8) | `""` |
| `SCHEMA_REGISTRY_PASSWORD_X` | Password for registry X (1-8) | `""` |
| `READONLY_X` | Read-only mode for registry X | `"false"` |

## Port Configuration

### Multi-Registry Environment
- **AKHQ UI**: `http://localhost:38080`
- **DEV Registry**: `http://localhost:38081` (read-write, backward compatibility)
- **PROD Registry**: `http://localhost:38082` (read-only, forward compatibility)
- **Kafka DEV**: `localhost:39092` (external), `9092` (internal)
- **Kafka PROD**: `localhost:39093` (external), `9093` (internal)

### Test Results Location
All test results are saved to:
- **Results Directory**: `tests/results/`
- **Logs**: `tests/results/*_test_*.log`
- **CSV Reports**: `tests/results/*_results_*.csv`
- **Summaries**: `tests/results/*_summary_*.txt`

## Quick Start Commands

### Complete Multi-Registry Setup
```bash
# 1. Install Docker Desktop if not installed
# 2. Start complete environment
cd tests
./start_multi_registry_environment.sh

# 3. Wait for startup (about 2 minutes)
# Services will report when ready

# 4. Run all tests
./run_multi_registry_tests.sh
```

### Minimal Setup (Single Registry)
```bash
# 1. Start single registry
cd tests
docker-compose -f docker-compose.test.yml up -d

# 2. Wait for startup (about 30 seconds)
sleep 30

# 3. Run basic tests
./run_comprehensive_tests.sh --basic
```

### External Registry Setup
```bash
# 1. Point to your Schema Registry
export SCHEMA_REGISTRY_URL="http://your-registry:38081"

# 2. Run basic tests
./run_comprehensive_tests.sh --basic
```

## Test Suites Available

### 1. Comprehensive Test Suite
- **File**: `run_comprehensive_tests.sh`
- **Purpose**: Single registry testing
- **Categories**: Basic, Workflows, Errors, Performance, Production

### 2. Multi-Registry Test Suite
- **File**: `run_multi_registry_tests.sh`
- **Purpose**: Multi-registry environment testing
- **Categories**: Configuration, Workflows, Tools, Performance

### 3. Migration Test Suite
- **File**: `run_migration_tests.sh`
- **Purpose**: Schema migration and comparison testing
- **Categories**: Migration, Comparison, Validation

### 4. Integration Test Suites
- **Files**: `run_integration_tests.sh`, `run_numbered_integration_tests.sh`
- **Purpose**: Legacy integration testing

## Validation Checklist

After successful test execution:
- ✅ Check test results in `tests/results/`
- ✅ Review test summary for any failed tests
- ✅ Verify CSV results for performance metrics
- ✅ Check logs for detailed execution information
- ✅ Validate all 68 MCP tools are working
- ✅ Confirm multi-registry operations (if applicable)
- ✅ Test migration and comparison features (if applicable)

## Next Steps

After testing:
1. **Production Deployment**: Use `claude_desktop_docker_config.json` for Docker deployment
2. **Multi-Registry**: Use `claude_desktop_multi_registry_docker.json` for multi-registry
3. **Local Development**: Use `claude_desktop_config.json` for local testing
4. **Monitoring**: Set up monitoring using the production readiness test results 