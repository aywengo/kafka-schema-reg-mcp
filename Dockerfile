FROM python:3.11-slim

# Build arguments for metadata
ARG VERSION="dev"
ARG BUILD_DATE
ARG VCS_REF

# Metadata
LABEL org.opencontainers.image.title="Kafka Schema Registry MCP Server" \
      org.opencontainers.image.description="True MCP server for Kafka Schema Registry with 20 tools, context support, schema export, and Claude Desktop integration" \
      org.opencontainers.image.version="$VERSION" \
      org.opencontainers.image.created="$BUILD_DATE" \
      org.opencontainers.image.revision="$VCS_REF" \
      org.opencontainers.image.vendor="aywengo" \
      org.opencontainers.image.source="https://github.com/aywengo/kafka-schema-reg-mcp" \
      org.opencontainers.image.url="https://github.com/aywengo/kafka-schema-reg-mcp" \
      org.opencontainers.image.documentation="https://github.com/aywengo/kafka-schema-reg-mcp#readme"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash mcp
RUN chown -R mcp:mcp /app
USER mcp

# Command to run the MCP server
CMD ["python", "kafka_schema_registry_mcp.py"]