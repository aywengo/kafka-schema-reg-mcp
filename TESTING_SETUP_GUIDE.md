# Testing Setup Guide

This guide provides setup instructions for the unified Kafka Schema Registry MCP Server testing environment.

## Quick Start (Recommended)

### Unified Test Environment
```bash
# Start the unified test environment and run all tests
cd tests
./run_all_tests.sh

# Or run essential tests only (faster)
./run_all_tests.sh --quick

# Keep environment running for debugging
./run_all_tests.sh --no-cleanup
```

This automatically sets up:
- **AKHQ UI**: http://localhost:38080 (monitoring interface)
- **DEV Registry**: http://localhost:38081 (primary registry)
- **PROD Registry**: http://localhost:38082 (secondary registry)
- **Kafka DEV**: localhost:9092 
- **Kafka PROD**: localhost:39093

## Option 1: Automated Testing (Recommended)

### Prerequisites
1. Download Docker Desktop: https://www.docker.com/products/docker-desktop/
2. Install and start Docker Desktop
3. Verify installation: `docker --version`
4. Ensure ports 38080-38082 and 9092 are available

### Run Unified Test Environment
```bash
# Complete automated testing (recommended)
cd tests
./run_all_tests.sh

# Verify services manually (if needed):
curl http://localhost:38081/subjects  # DEV Registry
curl http://localhost:38082/subjects  # PROD Registry  
curl http://localhost:38080/api/health # AKHQ UI
```

### Manual Environment Control
```bash
# Start environment manually
cd tests
./start_test_environment.sh multi

# Run individual tests
python3 test_basic_server.py

# Stop environment
./stop_test_environment.sh clean
```

## Option 2: Manual Environment Modes

You can start specific environment configurations:

```bash
# DEV only (single registry testing)
cd tests
./start_test_environment.sh dev

# Multi-registry (both DEV and PROD)
./start_test_environment.sh multi

# With monitoring UI
./start_test_environment.sh ui

# Verify services
curl http://localhost:38081/subjects

# Run tests
./run_all_tests.sh --quick
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

The unified test runner includes all test categories automatically:

### Unified Test Options
```bash
# Complete test suite (all categories)
./run_all_tests.sh

# Essential tests only (faster execution)
./run_all_tests.sh --quick

# Keep environment running for debugging
./run_all_tests.sh --no-cleanup

# Show all available options
./run_all_tests.sh --help
```

### Individual Test Files
```bash
# Run specific test files manually
python3 test_basic_server.py           # Basic functionality
python3 test_multi_registry_mcp.py     # Multi-registry features
python3 test_production_readiness.py   # Production readiness
python3 test_all_tools_validation.py   # All MCP tools
python3 test_batch_cleanup.py          # Batch operations
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

### Unified Environment
- **AKHQ UI**: `http://localhost:38080` (monitoring and management)
- **DEV Registry**: `http://localhost:38081` (primary registry)
- **PROD Registry**: `http://localhost:38082` (secondary registry) 
- **Kafka DEV**: `localhost:9092` (primary Kafka)
- **Kafka PROD**: `localhost:39093` (secondary Kafka)

### Test Results Location
All test results are saved to:
- **Results Directory**: `tests/results/`
- **Logs**: `tests/results/*_test_*.log`
- **CSV Reports**: `tests/results/*_results_*.csv`
- **Summaries**: `tests/results/*_summary_*.txt`

## Quick Start Commands

### Complete Unified Setup (Recommended)
```bash
# 1. Install Docker Desktop if not installed
# 2. Run complete test suite with automatic environment management
cd tests
./run_all_tests.sh

# Automatically handles:
# - Environment startup (about 2 minutes)
# - All test execution (~28 test categories)  
# - Environment cleanup
# - Detailed reporting
```

### Manual Environment Control
```bash
# 1. Start environment manually
cd tests
./start_test_environment.sh multi

# 2. Wait for startup (about 1-2 minutes)
# Services will report when ready

# 3. Run tests
./run_all_tests.sh --quick

# 4. Stop environment
./stop_test_environment.sh clean
```

### External Registry Setup
```bash
# 1. Point to your Schema Registry
export SCHEMA_REGISTRY_URL="http://your-registry:38081"

# 2. Run tests against external registry
./run_all_tests.sh --quick
```

## Test Suites Available

### 1. Unified Test Suite (Primary)
- **File**: `run_all_tests.sh`
- **Purpose**: Comprehensive testing of all functionality
- **Categories**: Basic server, Multi-registry, Production readiness, All tools, Batch operations
- **Features**: Automatic environment management, detailed reporting, timeout protection

### 2. Individual Test Files
- **test_basic_server.py**: Core MCP server functionality
- **test_multi_registry_mcp.py**: Multi-registry operations and environment detection
- **test_production_readiness.py**: Production validation and performance testing  
- **test_all_tools_validation.py**: Comprehensive MCP tool validation (~48 tools)
- **test_batch_cleanup.py**: Batch cleanup and bulk operations

## Validation Checklist

After successful test execution:
- ✅ Check test results in `tests/results/`
- ✅ Review test summary for any failed tests (~28 test categories)
- ✅ Verify CSV results for performance metrics
- ✅ Check logs for detailed execution information
- ✅ Validate all MCP tools are working (~48 tools tested)
- ✅ Confirm multi-registry operations (automatic environment detection)
- ✅ Verify timeout protection and error handling

## Next Steps

After testing:
1. **Production Deployment**: Use `claude_desktop_docker_config.json` for Docker deployment
2. **Multi-Registry**: Use `claude_desktop_multi_registry_docker.json` for multi-registry
3. **Local Development**: Use `claude_desktop_config.json` for local testing
4. **Monitoring**: Set up monitoring using the production readiness test results 