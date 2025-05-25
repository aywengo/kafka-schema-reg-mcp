FROM python:3.11-slim

# Build arguments for metadata
ARG VERSION="dev"
ARG BUILD_DATE
ARG VCS_REF

# Metadata
LABEL org.opencontainers.image.title="Kafka Schema Registry MCP Server" \
      org.opencontainers.image.description="Message Control Protocol server for Kafka Schema Registry with Context Support, Configuration Management, Mode Control, and Schema Export" \
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

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["python", "mcp_server.py"]