#!/bin/bash

# Test script for Docker build and run
set -e

echo "🚀 Building Docker image with improved Dockerfile..."

# Build the Docker image using the improved Dockerfile
docker build -f Dockerfile.glama -t mcp-server-glama .

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