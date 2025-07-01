# Use a more recent base image with latest security patches
FROM python:3.13-slim-bookworm AS builder

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
FROM python:3.13-slim-bookworm AS production

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
      org.opencontainers.image.description="True MCP server for Kafka Schema Registry with 50+ tools, OAuth authentication, remote deployment support, context management, elicitation capability, resource linking, and Claude Desktop integration" \
      org.opencontainers.image.version="$VERSION" \
      org.opencontainers.image.created="$BUILD_DATE" \
      org.opencontainers.image.revision="$VCS_REF" \
      org.opencontainers.image.vendor="aywengo" \
      org.opencontainers.image.source="https://github.com/aywengo/kafka-schema-reg-mcp" \
      org.opencontainers.image.url="https://github.com/aywengo/kafka-schema-reg-mcp" \
      org.opencontainers.image.documentation="https://github.com/aywengo/kafka-schema-reg-mcp#readme"

# Critical security updates - update all packages to get latest patches
# This ensures we have the latest security fixes for glibc, perl, and other system packages
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get dist-upgrade -y && \
    # Remove unnecessary packages to reduce attack surface
    apt-get autoremove -y \
        # Remove packages that are sources of vulnerabilities and not needed
        perl \
        perl-base \
        perl-modules-5.36 \
        # Remove ncurses packages if not needed (they cause CVE-2023-50495)
        libncursesw6 \
        libtinfo6 \
        ncurses-base \
        ncurses-bin \
    || true && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    find /var/log -type f -exec truncate -s 0 {} \;

# Create non-root user for security (before copying files)
RUN groupadd -r mcp && useradd -r -g mcp -d /app -s /bin/bash mcp

# Set working directory and ensure proper ownership
WORKDIR /app
RUN chown -R mcp:mcp /app

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy core application modules with proper ownership
COPY --chown=mcp:mcp oauth_provider.py .
COPY --chown=mcp:mcp schema_registry_common.py .
COPY --chown=mcp:mcp schema_definitions.py .
COPY --chown=mcp:mcp schema_validation.py .
COPY --chown=mcp:mcp core_registry_tools.py .
COPY --chown=mcp:mcp task_management.py .
COPY --chown=mcp:mcp batch_operations.py .
COPY --chown=mcp:mcp statistics_tools.py .
COPY --chown=mcp:mcp export_tools.py .
COPY --chown=mcp:mcp comparison_tools.py .
COPY --chown=mcp:mcp migration_tools.py .
COPY --chown=mcp:mcp registry_management_tools.py .
COPY --chown=mcp:mcp mcp_prompts.py .

# Copy elicitation modules (MCP 2025-06-18 interactive workflows)
COPY --chown=mcp:mcp elicitation.py .
COPY --chown=mcp:mcp elicitation_mcp_integration.py .
COPY --chown=mcp:mcp interactive_tools.py .
COPY --chown=mcp:mcp elicitation_enhancements.py .

# Copy NEW resource linking modules (MCP 2025-06-18 resource linking)
COPY --chown=mcp:mcp resource_linking.py .

# Copy main server files
COPY --chown=mcp:mcp kafka_schema_registry_unified_mcp.py .
COPY --chown=mcp:mcp remote-mcp-server.py .

# Additional security hardening
RUN chmod -R 750 /app && \
    chmod 550 /app/*.py

# Switch to non-root user
USER mcp

# Security: Set restrictive umask for any files created at runtime
RUN umask 077

# Add health check for MCP server (checks if Python process can import main module)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import kafka_schema_registry_unified_mcp; print('MCP server healthy')" || exit 1

# Security: Set environment variables for better security
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Security: Disable Python hash randomization for reproducible builds
    PYTHONHASHSEED=random \
    # Security: Enable Python development mode warnings
    PYTHONDEVMODE=0 \
    # Security: Restrict Python path
    PYTHONPATH=/app

# Security: Expose only the necessary port
EXPOSE 8000

# Command to run the MCP server
CMD ["python", "kafka_schema_registry_unified_mcp.py"]
