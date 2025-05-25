# Kafka Schema Registry MCP Server v1.3.0

A comprehensive Message Control Protocol (MCP) server that provides a REST API interface for Kafka Schema Registry operations, including advanced **Schema Context** support for logical schema grouping and management, **Configuration Management** for compatibility settings, **Mode Control** for operational state management, and **comprehensive Schema Export** capabilities for backup, migration, and schema documentation.

## ✨ Features

- **Complete Schema Management**: Register, retrieve, and manage Avro schemas
- **Schema Contexts**: Logical grouping with separate "sub-registries" 
- **Configuration Management**: Control compatibility levels globally and per-subject
- **Mode Control**: Manage operational states (READWRITE, READONLY, IMPORT)
- **Schema Export**: Comprehensive export capabilities with JSON, Avro IDL, and ZIP bundle formats
- **Version Control**: Handle multiple schema versions with compatibility checking
- **Authentication Support**: Optional basic authentication for Schema Registry
- **Compatibility Testing**: Verify schema evolution compatibility
- **Subject Management**: List and delete schema subjects
- **Context Isolation**: Schemas in different contexts are completely isolated
- **Docker Support**: Easy deployment with Docker Compose and pre-built DockerHub images
- **Multi-Platform Support**: AMD64 and ARM64 architectures
- **Security Scanning**: Automated vulnerability scanning with Trivy
- **CI/CD Ready**: GitHub Actions workflows for automated builds and publishing
- **Comprehensive Testing**: Full integration and unit test coverage

## 🏗️ Architecture

- **FastAPI-based MCP Server**: Modern async REST API with automatic OpenAPI docs
- **Kafka Schema Registry**: Backend for schema storage and management  
- **KRaft Mode**: Uses modern Kafka without Zookeeper dependency
- **Context-Aware Operations**: All endpoints support optional context parameters
- **Flexible Context Specification**: Context via request body or query parameters
- **Enterprise-Ready Configuration**: Granular control over compatibility and operational modes
- **Multi-Format Export**: JSON, Avro IDL, and ZIP bundle export formats

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)

### Option 1: Using Pre-built DockerHub Image (Recommended)
```bash
# Quick start with pre-built image
docker-compose up -d
```

The `docker-compose.override.yml` file automatically uses the pre-built image from DockerHub instead of building locally.

### Option 2: Using DockerHub Image Directly
```bash
# Run MCP server directly (latest version)
docker run -p 38000:8000 aywengo/kafka-schema-reg-mcp:latest

# Run specific version
docker run -p 38000:8000 aywengo/kafka-schema-reg-mcp:v1.3.0

# With environment variables
docker run -p 38000:8000 \
  -e SCHEMA_REGISTRY_URL=http://your-schema-registry:8081 \
  aywengo/kafka-schema-reg-mcp:latest
```

**Available Docker Tags:**
- `latest` - Latest stable release
- `v1.3.0` - Specific version (with export functionality)
- `v1.2.0` - Previous version (configuration management)
- Multi-platform support: `linux/amd64`, `linux/arm64`

### Option 3: Build from Source
```bash
# Remove override file to build locally
mv docker-compose.override.yml docker-compose.override.yml.bak
docker-compose up -d --build
```

This starts:
- **Kafka** (KRaft mode): `localhost:39092`
- **Schema Registry**: `localhost:38081` 
- **MCP Server**: `localhost:38000`
- **AKHQ UI**: `localhost:38080` (Kafka management UI)

### Health Check
```bash
curl http://localhost:38000/
# {"message": "Kafka Schema Registry MCP Server with Context Support"}
```

## 📋 API Overview

The MCP server provides comprehensive REST API endpoints for all Schema Registry operations:

### **Core Operations**
- **Schema Management**: Register, retrieve, and manage Avro schemas with versioning
- **Context Management**: Create and manage logical schema groupings
- **Subject Management**: List, delete, and manage schema subjects
- **Compatibility Testing**: Validate schema evolution before registration

### **Advanced Features**  
- **Configuration Management**: Global and subject-level compatibility controls
- **Mode Control**: Operational state management (READWRITE, READONLY, IMPORT)
- **Schema Export**: 17 export endpoints with JSON, Avro IDL, and ZIP bundle formats
- **Context-Aware Operations**: All endpoints support optional context parameters

### **Quick Example**
```bash
# Register a schema
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-events",
    "schema": {"type": "record", "name": "User", "fields": [...]},
    "context": "production"
  }'

# Export schemas
curl http://localhost:38000/export/schemas/user-events?format=avro_idl
```

**📖 Complete API Documentation**: [API Reference](docs/api-reference.md)

## 🎯 Key Capabilities

### **📦 Schema Export System**
Comprehensive export functionality with 17 endpoints supporting backup, migration, and documentation:
- **Multiple Formats**: JSON, Avro IDL, ZIP bundles
- **Flexible Scopes**: Single schemas, subjects, contexts, or global exports
- **Use Cases**: Environment promotion, disaster recovery, compliance auditing, documentation generation

**📖 Detailed Guide**: [API Reference - Export Endpoints](docs/api-reference.md#export-endpoints)

### **🏗️ Schema Contexts** 
Powerful logical grouping for enterprise schema management:
- **Environment Isolation**: Separate development, staging, production
- **Multi-Tenancy**: Client-specific schema isolation
- **Team Boundaries**: Organize schemas by development teams
- **Operational Benefits**: Namespace collision prevention, context-aware governance

**📖 Real-World Examples**: [Use Cases - Enterprise Scenarios](docs/use-cases.md#-enterprise-use-cases)

### **⚙️ Configuration & Mode Control**
Enterprise-grade operational control:
- **Compatibility Management**: Global and subject-level compatibility controls
- **Operational Modes**: READWRITE, READONLY, IMPORT for controlled access
- **Context-Aware Settings**: Different rules per environment
- **Governance**: Policy enforcement and change control

**📖 Complete Reference**: [API Reference - Configuration](docs/api-reference.md#configuration-management)

## 🔐 Authentication

Optional basic authentication support. Set environment variables:
```bash
export SCHEMA_REGISTRY_USER="your-username"
export SCHEMA_REGISTRY_PASSWORD="your-password"
```

**📖 Security Setup**: [Deployment Guide - Security](docs/deployment.md#-security-considerations)

## 🧪 Testing

Comprehensive test suite with 53 passing tests covering all functionality:
- ✅ **53 PASSED**, ⚠️ **1 SKIPPED** (auth), ❌ **0 FAILED**
- ✅ **17 Export Tests** covering all export scenarios and formats
- ✅ **Context Isolation** verification and multi-environment testing
- ✅ **Error Handling** for invalid requests and edge cases

```bash
# Run all tests
./run_integration_tests.sh
```

**📖 Testing Guide**: [Deployment Guide - Testing](docs/deployment.md#-troubleshooting)

## 🚀 Production Deployment

Production-ready with pre-built DockerHub images and comprehensive deployment options:

```bash
# Quick production start with pre-built images
docker-compose up -d

# Or direct Docker usage
docker run -d -p 38000:8000 aywengo/kafka-schema-reg-mcp:latest
```

**📖 Complete Guide**: [Deployment Guide](docs/deployment.md) - Docker Compose, Kubernetes, cloud platforms, monitoring, CI/CD

## 🔧 Development

Quick local development setup:

```bash
# Local Python development
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && python mcp_server.py

# Docker development
mv docker-compose.override.yml docker-compose.override.yml.bak
docker-compose build --no-cache mcp-server && docker-compose up -d
```

**📖 Development Guide**: [Deployment Guide - Development](docs/deployment.md#-local-development)

## 📚 Documentation

Comprehensive documentation covering all aspects:

| Guide | Purpose |
|-------|---------|
| **[API Reference](docs/api-reference.md)** | Complete endpoint documentation with examples |
| **[Use Cases](docs/use-cases.md)** | Real-world scenarios and implementation patterns |
| **[IDE Integration](docs/ide-integration.md)** | VS Code, Claude Code, and Cursor setup guides |
| **[Deployment Guide](docs/deployment.md)** | Docker, Kubernetes, cloud platforms, CI/CD |

### 🛠️ IDE Integration
- **🔵 VS Code**: Extensions, workspace configuration, REST client testing
- **🤖 Claude Code**: AI-assisted schema development and context management  
- **⚡ Cursor**: AI-powered development with schema generation and visualization

**📖 Setup Instructions**: [IDE Integration Guide](docs/ide-integration.md)

## 🔗 Schema Registry Integration

Integrates with [Confluent Schema Registry](https://docs.confluent.io/platform/current/schema-registry/fundamentals/index.html) supporting multiple formats (Avro, JSON, Protobuf), schema evolution, and context-based namespace management.

**📖 Integration Details**: [Use Cases - Schema Registry Integration](docs/use-cases.md#-schema-registry-integration)

---

## 🎉 Production Ready

**✅ 53 PASSED** tests with comprehensive validation of all features including export functionality, context management, and enterprise controls.

**🐳 DockerHub Ready**: `aywengo/kafka-schema-reg-mcp` with multi-platform support (AMD64/ARM64), automated CI/CD, and security scanning.

**🆕 v1.3.0 Features**: 
- 17 Schema Export endpoints (JSON, Avro IDL, ZIP bundles)
- Multi-scope exports (schema, subject, context, global)
- Enhanced CI/CD with automated DockerHub publishing
- Production-grade security scanning and monitoring

**📈 Previous Releases**: v1.2.0 (Configuration Management), v1.1.0 (Schema Contexts), v1.0.0 (Core MCP)