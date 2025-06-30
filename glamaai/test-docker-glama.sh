#!/bin/bash

# Test script for Docker build and run from glamaai/ folder
set -e

echo "🚀 Building Docker image with improved Dockerfile from glamaai/ folder..."

# Navigate to repository root for build context
cd "$(dirname "$0")/.."

# Build the Docker image using the Dockerfile from glamaai/ folder
docker build -f glamaai/Dockerfile.glama -t mcp-server-glama .

echo "✅ Docker image built successfully!"

echo "🧪 Testing Docker container..."

# Test run with environment variables
echo "Starting container with test configuration..."
docker run -it --rm \
    -e MCP_PROXY_DEBUG=true \
    -e MCP_HOST=0.0.0.0 \
    -e MCP_PATH=/mcp \
    -e MCP_PORT=8000 \
    -e READONLY=false \
    -e SCHEMA_REGISTRY_PASSWORD="s3cr3t-p@ssw0rd!" \
    -e SCHEMA_REGISTRY_URL="http://schema-registry.example.com:8081" \
    -e SCHEMA_REGISTRY_USER="schema_admin" \
    -p 8000:8000 \
    mcp-server-glama

echo "🎉 Test completed!"