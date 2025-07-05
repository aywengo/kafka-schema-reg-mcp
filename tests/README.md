# Kafka Schema Registry MCP Server Tests

This directory contains comprehensive tests for the **Unified Kafka Schema Registry MCP Server** (`kafka_schema_registry_unified_mcp.py`).

## Overview

The unified server automatically detects whether to run in single-registry or multi-registry mode based on environment variables. The unified test infrastructure provides a single Docker setup and comprehensive test runner for all scenarios:

- **Single Registry Tests**: Use DEV registry (localhost:38081) from the unified environment
- **Multi-Registry Tests**: Use both DEV (38081) and PROD (38082) registries
- **Unified Environment**: Single `docker-compose.yml` supports both testing modes

## Test Structure

### Basic Tests
- `test_basic_server.py` - Server import and initialization tests
- `test_mcp_server.py` - MCP protocol connectivity tests
- `test_config.py` - Configuration management tests
- `test_remote_mcp_server.py` - Remote MCP server deployment functionality
- `test_remote_mcp_metrics.py` - Remote MCP server metrics and monitoring
- `test_simple_python.py` - Basic Python environment validation

### Integration Tests
- `test_integration.py` - Comprehensive schema registry operations
- `advanced_mcp_test.py` - Advanced MCP functionality
- `test_docker_mcp.py` - Docker container integration
- `test_oauth.py` - OAuth authentication and provider configurations
- `test_github_oauth.py` - GitHub OAuth integration and token validation
- `test_user_roles.py` - OAuth user role assignment and scope extraction

### Mode-Specific Tests
- `test_viewonly_mode.py` - VIEWONLY mode enforcement
- `test_multi_registry_mcp.py` - Multi-registry mode functionality
- `test_numbered_integration.py` - Numbered environment variable configuration

### Advanced Features
- `test_batch_cleanup.py` - Batch cleanup operations
- `test_migration_integration.py` - Schema migration functionality
- `test_performance_load.py` - Performance and load testing
- `test_error_handling.py` - Error handling and recovery

### Remote MCP Server Tests
- `test_remote_mcp_server.py` - Remote deployment functionality and transport configuration
- `test_remote_mcp_metrics.py` - Comprehensive metrics and monitoring testing:
  - RemoteMCPMetrics class functionality and initialization
  - Schema Registry custom metrics (`mcp_schema_registry_*`)
  - Prometheus metrics format validation and content verification
  - Health check endpoint testing (/health, /ready)
  - OAuth validation metrics and error tracking
  - Registry statistics collection with caching
  - Response time tracking and performance metrics
  - Integration testing with monitoring endpoints

### Validation Tests
- `test_all_tools_validation.py` - Validates all MCP tools
- `test_counting_tools.py` - Schema counting and statistics
- `validate_single_registry_runner.py` - Test runner validation

## Running Tests

### Prerequisites

1. **Install Dependencies**:
   ```bash
   pip install -r ../requirements.txt
   ```

2. **Docker Requirements**:
   - Docker Desktop running
   - At least 4GB RAM allocated to Docker
   - Ports 38080-38082 and 9092 available

### Test Runners

#### Unified Test Runner (Recommended)
```bash
# Run complete test suite with automatic environment management
./run_all_tests.sh

# Quick test run (essential tests only)
./run_all_tests.sh --quick

# Keep environment running after tests for debugging
./run_all_tests.sh --no-cleanup

# Show all available options
./run_all_tests.sh --help
```

**This is the recommended way to run tests.** It automatically:
- Starts the unified multi-registry environment
- Runs comprehensive test suite (both single and multi-registry tests)
- Generates detailed reports with timing and success rates
- Cleans up environment when complete

#### Manual Environment Management
```bash
# Start unified environment (supports both single and multi-registry tests)
./start_test_environment.sh multi

# Run individual tests
python3 test_basic_server.py
python3 test_multi_registry_mcp.py

# Stop environment
./stop_test_environment.sh clean
```

#### Environment Mode Options
```bash
# Start only DEV registry (single-registry tests)
./start_test_environment.sh dev

# Start full environment (multi-registry tests)
./start_test_environment.sh multi

# Start with UI monitoring
./start_test_environment.sh ui
```

#### Individual Tests
```bash
# Basic server functionality
python3 test_basic_server.py

# MCP connectivity
python3 test_mcp_server.py

# Integration tests
python3 test_integration.py

# Multi-registry mode
python3 test_multi_registry_mcp.py
```

## Environment Configuration

The unified test environment automatically configures itself, but you can override settings:

### Automatic Configuration (Recommended)
The test scripts automatically set up the correct environment variables. No manual configuration needed when using `./run_all_tests.sh` or `./start_test_environment.sh`.

### Manual Configuration (Advanced)
If running tests individually, you can set:

#### Single Registry Mode
```bash
export SCHEMA_REGISTRY_URL="http://localhost:38081"
```

#### Multi-Registry Mode  
```bash
# Registry 1 (Development)
export SCHEMA_REGISTRY_NAME_1="dev"
export SCHEMA_REGISTRY_URL_1="http://localhost:38081"
export VIEWONLY_1="false"

# Registry 2 (Production)
export SCHEMA_REGISTRY_NAME_2="prod"
export SCHEMA_REGISTRY_URL_2="http://localhost:38082"
export VIEWONLY_2="false"
```

**Note**: Authentication variables (`SCHEMA_REGISTRY_USER_*`, `SCHEMA_REGISTRY_PASSWORD_*`) are optional for the test environment.

## Unified Docker Environment

The test infrastructure uses a single `docker-compose.yml` that provides both single and multi-registry testing capabilities:

### Service URLs
| Service | URL | Usage |
|---------|-----|-------|
| **Kafka DEV** | `localhost:9092` | Primary Kafka for single-registry tests |
| **Schema Registry DEV** | `localhost:38081` | Primary registry (all tests) |
| **Kafka PROD** | `localhost:39093` | Secondary Kafka for multi-registry tests |
| **Schema Registry PROD** | `localhost:38082` | Secondary registry for multi-registry tests |
| **AKHQ UI** | `http://localhost:38080` | Web UI for monitoring and management |

### Environment Modes
- **DEV Only** (`./start_test_environment.sh dev`): Starts only DEV services for single-registry tests
- **Full Environment** (`./start_test_environment.sh multi`): Starts all services for comprehensive testing
- **With UI** (`./start_test_environment.sh ui`): Full environment plus monitoring UI

## Test Categories

The tests are organized in logical progression from basic to advanced:

### 🔧 Basic Tests (Foundation)
- Server import and initialization
- MCP protocol connectivity
- Configuration management
- Python environment validation

### ⚡ Integration Tests (Core Operations)
- Schema operations (register, get, list, versions)
- VIEWONLY mode enforcement
- Schema counting and statistics
- Context management
- Docker integration

### 🏢 Multi-Registry Tests (Multi-Instance Operations)
- Multi-registry server functionality
- Configuration validation
- Numbered environment variables
- Default context handling
- Basic batch operations

### 🚀 Advanced Tests (Comparison & Migration)
**These complex operations are run last:**
- Schema migration between registries
- Cross-registry comparison
- ID preservation migration
- All versions migration
- Docker migration configuration
- End-to-end workflows
- Performance and load testing
- Production readiness validation

### 🛡️ Safety Features (Tested Throughout)
- VIEWONLY mode protection
- Error handling and recovery
- Input validation
- Production safety measures

## Troubleshooting

### Common Issues

1. **Environment Not Starting**:
   ```bash
   # Check Docker status
   docker ps
   
   # Clean restart
   ./stop_test_environment.sh clean
   ./start_test_environment.sh multi
   ```

2. **Port Conflicts**:
   ```bash
   # Check what's using required ports
   lsof -i :38081
   lsof -i :38082
   
   # Kill conflicting processes and restart
   ./stop_test_environment.sh clean
   ./start_test_environment.sh
   ```

3. **Test Failures**:
   ```bash
   # Check detailed test logs
   ls -la tests/results/
   
   # Run individual test for debugging
   python3 test_basic_server.py
   
   # Check environment health
   curl http://localhost:38081/subjects
   curl http://localhost:38082/subjects
   ```

4. **Import Errors**:
   ```bash
   # Ensure you're in the project root
   cd ..
   python3 -c "import kafka_schema_registry_unified_mcp"
   ```

### Environment Validation
```bash
# Quick connectivity check
python3 quick_registry_check.py

# Comprehensive environment validation
./run_all_tests.sh --quick
```

### Service Status Check
```bash
# Check all services
docker-compose ps

# Check specific service logs
docker logs kafka-dev
docker logs schema-registry-dev
docker logs schema-registry-prod

# Web UI monitoring
open http://localhost:38080
```

## Test Results

Test results are saved in `tests/results/` with timestamps:
- `comprehensive_test_YYYYMMDD_HHMMSS.log` - Full test output
- `test_summary_YYYYMMDD_HHMMSS.txt` - Summary report
- `test_results_YYYYMMDD_HHMMSS.csv` - Machine-readable results

## Contributing

When adding new tests:

1. **Follow Naming Convention**: `test_*.py` or `*_test.py`
2. **Use Unified Server**: Import `kafka_schema_registry_unified_mcp`
3. **Handle Both Modes**: Test should work in single or multi-registry mode
4. **Add Documentation**: Update this README with new test descriptions
5. **Update Runners**: Add to appropriate test runner scripts

## Migration from Separate Servers

If you have existing tests that reference the old separate servers:

1. **Run Update Script**:
   ```bash
   python3 update_test_references.py
   ```

2. **Update Environment Variables**: Use numbered variables for multi-registry mode

3. **Test Compatibility**: Run validation scripts to ensure everything works

The unified server maintains 100% backward compatibility with existing configurations. 