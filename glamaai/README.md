# Glama.ai Docker Deployment

This directory contains the improved Docker setup for deploying the Kafka Schema Registry MCP Server with Glama.ai.

## Files in this Directory

- `Dockerfile.glama` - Improved Dockerfile that fixes issues from the original proposal
- `test-docker-glama.sh` - Test script for validating the Docker build and deployment
- `README.md` - This documentation file

**Note**: The `entrypoint.sh` file is located in the repository root and is referenced by the Dockerfile.

## Key Improvements

### Fixed Issues from Original Dockerfile

1. **Redundant Python Installation**: Removed duplicate Python installation steps
2. **Optimized Dependencies**: Combined system package installation for efficiency
3. **Security**: Added non-root user execution for container security
4. **Health Checks**: Added proper health check for container monitoring
5. **Error Handling**: Improved error handling in entrypoint script

### Enhanced Features

- **Environment Validation**: Entrypoint script validates required environment variables
- **Flexible Execution**: Supports both mcp-proxy and direct Python execution
- **Comprehensive Logging**: Added timestamped logging for better debugging
- **Build Optimization**: Reduced image size and build time

## Usage

### Building the Image

From the repository root:
```bash
# Build with the improved Dockerfile
docker build -f glamaai/Dockerfile.glama -t mcp-server-glama .
```

Or using the test script from this directory:
```bash
cd glamaai
chmod +x test-docker-glama.sh
./test-docker-glama.sh
```

### Running the Container

```bash
# Run with environment variables
docker run -it --rm \
    -e MCP_PROXY_DEBUG=true \
    -e MCP_HOST=0.0.0.0 \
    -e MCP_PATH=/mcp \
    -e MCP_PORT=8000 \
    -e VIEWONLY=false \
    -e SCHEMA_REGISTRY_PASSWORD="your-password" \
    -e SCHEMA_REGISTRY_URL="http://your-schema-registry:8081" \
    -e SCHEMA_REGISTRY_USER="your-username" \
    -p 8000:8000 \
    mcp-server-glama
```

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `SCHEMA_REGISTRY_URL` | Schema Registry endpoint | Yes | - |
| `SCHEMA_REGISTRY_USER` | Schema Registry username | No | - |
| `SCHEMA_REGISTRY_PASSWORD` | Schema Registry password | No | - |
| `MCP_HOST` | Server bind address | No | `0.0.0.0` |
| `MCP_PORT` | Server port | No | `8000` |
| `MCP_PATH` | Server path | No | `/mcp` |
| `VIEWONLY` | View-only mode | No | `false` |
| `MCP_PROXY_DEBUG` | Enable proxy debug mode | No | - |

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────────┐
│   Glama.ai      │───▶│  mcp-proxy   │───▶│  Python MCP Server  │
│   Inspector     │    │  (Node.js)   │    │  (FastMCP)          │
└─────────────────┘    └──────────────┘    └─────────────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │ Schema       │
                       │ Registry     │
                       └──────────────┘
```

## Troubleshooting

### Common Issues

1. **Missing entrypoint.sh**: Ensure the file exists in the repository root
2. **Environment Variables**: Check that `SCHEMA_REGISTRY_URL` is set
3. **Network Issues**: Verify Schema Registry connectivity
4. **Permission Errors**: Container runs as non-root user `mcp`
5. **Build Context**: Make sure to run docker build from repository root

### Debug Mode

Enable debug mode for mcp-proxy:

```bash
docker run ... -e MCP_PROXY_DEBUG=true mcp-server-glama
```

### Health Check

The container includes a health check that validates the Python MCP server:

```bash
# Check container health
docker ps
# Look for "healthy" status
```

## File Structure

```
repository-root/
├── entrypoint.sh              # Entrypoint script (referenced by Dockerfile)
├── glamaai/
│   ├── Dockerfile.glama       # Improved Dockerfile for Glama.ai
│   ├── test-docker-glama.sh   # Test script (run from this directory)
│   └── README.md              # This file
├── docs/
│   └── glama-integration.md   # Glama.ai integration documentation
└── ... (other project files)
```

## Security Considerations

- Container runs as non-root user `mcp`
- Environment variables are validated before execution
- Sensitive credentials should be passed via environment variables
- Consider using Docker secrets for production deployments

## Integration with Glama.ai

This setup is specifically designed for Glama.ai's `inspectMcpServerDockerImage` function and provides:

1. **Standardized Interface**: Compatible with Glama.ai's inspection tools
2. **mcp-proxy Integration**: Proper proxy setup for Glama.ai communication
3. **Health Monitoring**: Built-in health checks for reliability
4. **Security Compliance**: Non-root execution and proper permission handling

## Support

For issues with this deployment setup, please check:

1. Container logs: `docker logs <container-id>`
2. Health check status: `docker inspect <container-id>`
3. Environment configuration
4. Network connectivity to Schema Registry
5. File permissions and build context

For more detailed documentation, see `docs/glama-integration.md` in the repository root.