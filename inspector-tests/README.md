# MCP Inspector Tests

This directory contains MCP Inspector tests for the Kafka Schema Registry MCP Server. These tests validate that our published Docker images work correctly with the MCP protocol.

## Overview

The MCP Inspector is a powerful testing and debugging tool for MCP servers. We use it to:

- Test our released Docker images (`:stable`, `:latest`, and specific versions)
- Validate single and multi-registry configurations
- Ensure MCP tool functionality
- Debug issues with MCP protocol communication

## Prerequisites

- Node.js 22.7.5 or higher
- Docker and Docker Compose
- Running Schema Registry instances (handled by test scripts)

## Quick Start

### Test All Configurations

```bash
# Run a specific configuration (auto environment setup)
./run-inspector-tests.sh stable  # Single registry (DEV)
./run-inspector-tests.sh latest  # Single registry with :latest tag
./run-inspector-tests.sh multi   # Multi-registry (DEV+PROD)
```

### Test Specific Docker Version

```bash
# Test a specific Docker version
DOCKER_VERSION=v1.4.0 ./run-inspector-tests.sh stable

# Test latest version
DOCKER_VERSION=latest ./run-inspector-tests.sh multi
```

### Manual Testing with Inspector UI

```bash
# Start the test environment
cd ../tests
./start_test_environment.sh multi

# Launch Inspector UI and manually connect
cd ../inspector-tests
npx @mcpjam/inspector
```

## Configuration Files

### `config/inspector-config-stable.json`
Single registry configuration using the `:stable` Docker tag.

### `config/inspector-config-multi.json`
Multi-registry configuration with DEV and PROD registries.

### `config/inspector-config-latest.json`
Similar to stable but uses the `:latest` Docker tag.

## Environment Variables

Control test behavior with these environment variables:

```bash
# Skip starting the test environment (if already running)
SKIP_ENV_SETUP=true ./run-inspector-tests.sh

# Keep the test environment running after tests
CLEANUP_AFTER=false ./run-inspector-tests.sh

# Test specific Docker version
DOCKER_VERSION=v1.3.0 ./run-inspector-tests.sh
```

## GitHub Actions Integration

Tests run automatically on:
- Push to main/develop branches
- Pull requests
- Daily schedule (2 AM UTC)
- Manual workflow dispatch

### Running in CI

```yaml
# Triggered on push, PR, or schedule
name: MCP Inspector Tests

# Tests multiple Docker versions
strategy:
  matrix:
    docker-version: [stable, latest, v1.4.0]
```

## Interactive Testing

The MCP Inspector provides an interactive UI for testing:

1. **Connect to Server**: Automatically connects using the config file
2. **View Tools**: See all available MCP tools
3. **Execute Tools**: Run tools with parameter input
4. **View Logs**: Debug communication between Inspector and server
5. **Test with LLM**: Test your server against a real LLM

### Example Interactive Session

1. Launch Inspector:
   ```bash
   npx @mcpjam/inspector --config ./config/inspector-config-stable.json
   ```

2. In the browser at `http://localhost:6274`:
   - Click on "Tools" to see available operations
   - Select `list_subjects` and execute
   - View the response and logs

## Debugging

### Enable Debug Logging

```bash
# Set debug environment variable
DEBUG=* ./run-inspector-tests.sh
```

### Common Issues

1. **Port conflicts**: Ensure ports 38081 and 38082 are free
2. **Docker not running**: Start Docker Desktop/daemon
3. **Node version**: Requires Node.js 22.7.5+

### View Container Logs

```bash
# View MCP server logs
docker logs -f $(docker ps -q -f "ancestor=aywengo/kafka-schema-reg-mcp:stable")

# View Schema Registry logs
docker-compose -f ../tests/docker-compose.yml logs -f
```

## Writing Custom Tests

Create new test configurations in the `config/` directory:

```json
{
  "mcpServers": {
    "my-test": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "SCHEMA_REGISTRY_URL",
        "-e", "CUSTOM_ENV_VAR",
        "aywengo/kafka-schema-reg-mcp:stable"
      ],
      "env": {
        "SCHEMA_REGISTRY_URL": "http://host.docker.internal:8081",
        "CUSTOM_ENV_VAR": "value"
      }
    }
  }
}
```

## Integration with Development

During development, you can test local changes:

```bash
# Build local Docker image
cd ..
docker build -t kafka-schema-reg-mcp:local .

# Test with Inspector
cd inspector-tests
DOCKER_VERSION=local ./run-inspector-tests.sh
```

## Maintenance

- Update `package.json` when new Inspector versions are released
- Add new test configurations for new features
- Update GitHub Actions workflow for new test scenarios
