#!/bin/bash

# Exit on any error
set -e

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting Kafka Schema Registry MCP Server..."

# Set default environment variables if not provided
export MCP_HOST=${MCP_HOST:-"0.0.0.0"}
export MCP_PORT=${MCP_PORT:-"8000"}
export MCP_PATH=${MCP_PATH:-"/mcp"}
export READONLY=${READONLY:-"false"}

# Log environment configuration
log "Configuration:"
log "  Host: $MCP_HOST"
log "  Port: $MCP_PORT"
log "  Path: $MCP_PATH"
log "  Readonly: $READONLY"
log "  Schema Registry URL: ${SCHEMA_REGISTRY_URL:-"<not set>"}"
log "  Schema Registry User: ${SCHEMA_REGISTRY_USER:-"<not set>"}"

# Check required environment variables
if [ -z "$SCHEMA_REGISTRY_URL" ]; then
    log "ERROR: SCHEMA_REGISTRY_URL environment variable is required"
    exit 1
fi

# Activate Python virtual environment if it exists
if [ -d ".venv" ]; then
    log "Activating virtual environment..."
    source .venv/bin/activate
fi

# Check if mcp-proxy is available and Python script exists
if command -v mcp-proxy >/dev/null 2>&1 && [ -f "kafka_schema_registry_unified_mcp.py" ]; then
    log "Starting with mcp-proxy..."
    exec mcp-proxy python kafka_schema_registry_unified_mcp.py "$@"
elif [ -f "kafka_schema_registry_unified_mcp.py" ]; then
    log "Starting Python script directly..."
    exec python kafka_schema_registry_unified_mcp.py "$@"
else
    log "ERROR: kafka_schema_registry_unified_mcp.py not found"
    exit 1
fi