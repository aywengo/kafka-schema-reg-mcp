# Use a more recent base image with latest security patches
FROM python:3.13-slim-bookworm as builder

# Build arguments for metadata and multi-platform support
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG TARGETOS
ARG TARGETARCH
ARG VERSION="dev"
ARG BUILD_DATE
ARG VCS_REF

# Log build platform information
RUN echo "Building on $BUILDPLATFORM for $TARGETPLATFORM"

# Update package lists and upgrade all packages to latest versions to patch vulnerabilities
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    # Only install what we absolutely need for building
    gcc \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy requirements and install Python dependencies in builder stage
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Production stage with minimal attack surface
FROM python:3.13-slim-bookworm as production

# Build arguments for metadata and multi-platform support
ARG BUILDPLATFORM
ARG TARGETPLATFORM  
ARG TARGETOS
ARG TARGETARCH
ARG VERSION="dev"
ARG BUILD_DATE
ARG VCS_REF

# Log production platform information
RUN echo "Production stage on $BUILDPLATFORM for $TARGETPLATFORM ($TARGETARCH)"

# Metadata
LABEL org.opencontainers.image.title="Kafka Schema Registry MCP Server" \
      org.opencontainers.image.description="True MCP server for Kafka Schema Registry with 48 tools, OAuth authentication, remote deployment support, context management, and Claude Desktop integration" \
      org.opencontainers.image.version="$VERSION" \
      org.opencontainers.image.created="$BUILD_DATE" \
      org.opencontainers.image.revision="$VCS_REF" \
      org.opencontainers.image.vendor="aywengo" \
      org.opencontainers.image.source="https://github.com/aywengo/kafka-schema-reg-mcp" \
      org.opencontainers.image.url="https://github.com/aywengo/kafka-schema-reg-mcp" \
      org.opencontainers.image.documentation="https://github.com/aywengo/kafka-schema-reg-mcp#readme"

# Critical security updates - explicitly update vulnerable packages
RUN apt-get update && apt-get upgrade -y && \
    # Specifically update zlib and related packages to patch CVEs
    apt-get install -y --only-upgrade \
    zlib1g \
    zlib1g-dev \
    libaom3 \
    libaom-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && find /var/log -type f -exec truncate -s 0 {} \;

# Create non-root user for security (before copying files)
RUN groupadd -r mcp && useradd -r -g mcp -d /app -s /bin/bash mcp

# Set working directory and ensure proper ownership
WORKDIR /app
RUN chown -R mcp:mcp /app

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code with proper ownership
COPY --chown=mcp:mcp oauth_provider.py .
COPY --chown=mcp:mcp schema_registry_common.py .
COPY --chown=mcp:mcp core_registry_tools.py .
COPY --chown=mcp:mcp task_management.py .
COPY --chown=mcp:mcp batch_operations.py .
COPY --chown=mcp:mcp statistics_tools.py .
COPY --chown=mcp:mcp export_tools.py .
COPY --chown=mcp:mcp comparison_tools.py .
COPY --chown=mcp:mcp migration_tools.py .
COPY --chown=mcp:mcp mcp_prompts.py .
COPY --chown=mcp:mcp kafka_schema_registry_unified_mcp.py .
COPY --chown=mcp:mcp remote-mcp-server.py .

# Switch to non-root user
USER mcp

# Add health check for MCP server (checks if Python process can import main module)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import kafka_schema_registry_unified_mcp; print('MCP server healthy')" || exit 1

# Security: Set environment variables for better security
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Command to run the MCP server
CMD ["python", "kafka_schema_registry_unified_mcp.py"]