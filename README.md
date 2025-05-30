# Kafka Schema Registry MCP Server

A comprehensive **Message Control Protocol (MCP) server** that provides Claude Desktop and other MCP clients with tools for Kafka Schema Registry operations. Features include advanced **Schema Context** support for logical schema grouping, **Configuration Management** for compatibility settings, **Mode Control** for operational state management, and **comprehensive Schema Export** capabilities for backup, migration, and schema documentation.

> **🎯 True MCP Implementation**: This server uses the official MCP Python SDK and communicates via JSON-RPC over stdio, making it fully compatible with Claude Desktop and other MCP clients.

## ✨ Features

### **🤖 MCP Integration**
- **Claude Desktop Compatible**: Direct integration with Claude Desktop via MCP protocol
- **MCP Tools**: 20+ tools for schema operations, context management, configuration, and export
- **MCP Resources**: Real-time status and configuration information accessible to AI
- **JSON-RPC Protocol**: Standard MCP communication over stdio

### **📋 Schema Management**
- **Complete Schema Operations**: Register, retrieve, and manage Avro schemas via MCP tools
- **Schema Contexts**: Logical grouping with separate "sub-registries" 
- **Version Control**: Handle multiple schema versions with compatibility checking
- **Compatibility Testing**: Verify schema evolution before registration
- **Subject Management**: List and delete schema subjects through MCP

### **⚙️ Advanced Features**
- **Multi-Registry Support**: Connect to up to 8 Schema Registry instances simultaneously
- **Per-Registry READONLY Mode**: Individual readonly protection per registry for production safety
- **Cross-Registry Operations**: Compare, migrate, and synchronize schemas between registries
- **Configuration Management**: Control compatibility levels globally and per-subject
- **Mode Control**: Manage operational states (READWRITE, READONLY, IMPORT)
- **Schema Export**: Comprehensive export with JSON, Avro IDL formats
- **Context Isolation**: Schemas in different contexts are completely isolated
- **Authentication Support**: Optional basic authentication for Schema Registry

## 🏗️ Architecture

- **MCP Protocol Server**: Uses official MCP Python SDK with JSON-RPC over stdio
- **Kafka Schema Registry Integration**: Backend for schema storage and management  
- **KRaft Mode Support**: Works with modern Kafka without Zookeeper dependency
- **Context-Aware Operations**: All tools support optional context parameters
- **Claude Desktop Integration**: Direct integration with Claude Desktop via MCP configuration
- **Enterprise-Ready**: Granular control over compatibility and operational modes
- **Multi-Format Export**: JSON and Avro IDL export formats through MCP tools

## 🚀 Quick Start

### Prerequisites
- **Docker** (recommended) OR **Python 3.11+**
- **Claude Desktop** (for AI integration)
- **Kafka Schema Registry** (running and accessible)

### Option 1: Docker (Recommended)

#### Pull from DockerHub
```bash
# Latest stable release
docker pull aywengo/kafka-schema-reg-mcp:stable

# Or use latest (might be not released yet)
docker pull aywengo/kafka-schema-reg-mcp:latest

# Or specific version
docker pull aywengo/kafka-schema-reg-mcp:v1.4.0
```

#### Test the Docker image
```bash
# Test MCP server in Docker
python tests/test_docker_mcp.py
```

#### Use with existing infrastructure
```bash
# Start with docker-compose (includes Schema Registry)
docker-compose up -d
```

### Option 2: Local Installation

#### Step 1: Install Dependencies
```bash
# Clone the repository
git clone https://github.com/aywengo/kafka-schema-reg-mcp
cd kafka-schema-reg-mcp

# Install Python dependencies
pip install -r requirements.txt
```

#### Step 2: Configure Environment

**Single Registry Mode (Backward Compatible):**
```bash
# Basic Schema Registry connection
export SCHEMA_REGISTRY_URL="http://localhost:8081"
export SCHEMA_REGISTRY_USER=""           # Optional
export SCHEMA_REGISTRY_PASSWORD=""       # Optional
export READONLY="false"                  # Global readonly mode
```

**Multi-Registry Mode (New - Up to 8 Registries):**
```bash
# Registry 1 - Development
export SCHEMA_REGISTRY_NAME_1="development"
export SCHEMA_REGISTRY_URL_1="http://dev-schema-registry:8081"
export SCHEMA_REGISTRY_USER_1="dev-user"      # Optional
export SCHEMA_REGISTRY_PASSWORD_1="dev-pass"  # Optional
export READONLY_1="false"                     # Per-registry readonly

# Registry 2 - Production (with safety)
export SCHEMA_REGISTRY_NAME_2="production"
export SCHEMA_REGISTRY_URL_2="http://prod-schema-registry:8081"
export SCHEMA_REGISTRY_USER_2="prod-user"
export SCHEMA_REGISTRY_PASSWORD_2="prod-pass"
export READONLY_2="true"                      # Production safety
```

#### Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| **Single Registry Mode** | | | |
| `SCHEMA_REGISTRY_URL` | Schema Registry endpoint | `http://localhost:8081` | `http://schema-registry:8081` |
| `SCHEMA_REGISTRY_USER` | Username for authentication | *(empty)* | `admin` |
| `SCHEMA_REGISTRY_PASSWORD` | Password for authentication | *(empty)* | `password123` |
| `READONLY` | Global read-only mode | `false` | `true` |
| **Multi-Registry Mode** | | | |
| `SCHEMA_REGISTRY_NAME_X` | Registry alias (X=1-8) | *(required)* | `production` |
| `SCHEMA_REGISTRY_URL_X` | Registry endpoint (X=1-8) | *(required)* | `http://prod-registry:8081` |
| `SCHEMA_REGISTRY_USER_X` | Username (X=1-8) | *(empty)* | `prod-user` |
| `SCHEMA_REGISTRY_PASSWORD_X` | Password (X=1-8) | *(empty)* | `prod-password` |
| `READONLY_X` | Per-registry readonly (X=1-8) | `false` | `true` |

#### 🔒 READONLY Mode (Production Safety Feature)

When `READONLY=true` is set, the MCP server blocks all modification operations while keeping read and export operations available. Perfect for production environments where you want to prevent accidental changes.

**Blocked Operations:**
- ❌ Schema registration and deletion
- ❌ Context creation and deletion  
- ❌ Configuration changes
- ❌ Mode modifications

**Allowed Operations:**
- ✅ Schema browsing and retrieval
- ✅ Compatibility checking (read-only)
- ✅ All export operations
- ✅ Configuration reading

**Usage Examples:**
```bash
# Production environment with read-only protection
export READONLY=true
python kafka_schema_registry_mcp.py

# Docker with read-only mode
docker run -e READONLY=true -e SCHEMA_REGISTRY_URL=http://localhost:8081 aywengo/kafka-schema-reg-mcp:stable

# Claude Desktop configuration with read-only mode
{
  "env": {
    "SCHEMA_REGISTRY_URL": "http://localhost:8081",
    "READONLY": "true"
  }
}
```

#### Step 3: Test MCP Server
```bash
# Test the server directly
python tests/test_mcp_server.py
```

### Configure Claude Desktop

#### Ready-to-Use Configuration Examples

All configuration examples are available in the [`config-examples/`](config-examples/) directory with updated port configurations.

**Quick Setup:**
```bash
# Copy the configuration that matches your use case
cp config-examples/claude_desktop_stable_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Or for Linux
cp config-examples/claude_desktop_stable_config.json ~/.config/claude-desktop/config.json
```

#### Option A: Using Docker (Recommended)

**Stable Tag (Recommended for Production):**
```bash
# Use the pre-configured stable setup
cp config-examples/claude_desktop_stable_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Latest Tag:**
```bash
# Use the latest Docker image
cp config-examples/claude_desktop_docker_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Multi-Registry Setup:**
```bash
# For multi-environment schema management
cp config-examples/claude_desktop_multi_registry_docker.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

#### Option B: Local Python Installation
```bash
# For local development
cp config-examples/claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

#### Configuration Options Available

| Configuration | Use Case | Description |
|---------------|----------|-------------|
| `claude_desktop_stable_config.json` | **Production** | Docker stable tag, single registry |
| `claude_desktop_multi_registry_docker.json` | **Multi-Environment** | Docker with DEV/STAGING/PROD registries |
| `claude_desktop_config.json` | **Local Development** | Python local execution |
| `claude_desktop_readonly_config.json` | **Production Safety** | Read-only mode enforced |
| `claude_desktop_simple_multi.json` | **Simple Multi-Registry** | 2-registry setup (dev + prod) |

**📖 Complete Configuration Guide**: [`config-examples/README.md`](config-examples/README.md)

Copy the configuration to your Claude Desktop config file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

> **💡 Configuration Pattern**: The `-e VARIABLE_NAME` pattern (without values) in args combined with the `env` section is the recommended approach. This separates Docker arguments from configuration values, making the setup more maintainable and secure.

### Step 5: Use with Claude Desktop
1. Restart Claude Desktop
2. Look for the 🔨 tools icon in the interface
3. Start asking Claude to help with schema operations!

**Single Registry Example prompts:**
- "List all schema contexts"
- "Show me the subjects in the production context"
- "Register a new user schema with fields for id, name, and email"
- "Export all schemas from the staging context"

**Multi-Registry Example prompts:**
- "List all my Schema Registry instances"
- "Compare development and production registries"
- "Migrate user-events schema from staging to production"
- "Test connections to all registries"
- "Register a schema in the development registry"

## 📋 MCP Tools & Resources

The MCP server provides **20 comprehensive tools** and **2 resources** for all Schema Registry operations:

### **🔧 Available Tools**
- **Schema Management**: `register_schema`, `get_schema`, `get_schema_versions`, `check_compatibility`
- **Context Management**: `list_contexts`, `create_context`, `delete_context`
- **Subject Management**: `list_subjects`, `delete_subject`
- **Configuration Management**: `get_global_config`, `update_global_config`, `get_subject_config`, `update_subject_config`
- **Mode Control**: `get_mode`, `update_mode`, `get_subject_mode`, `update_subject_mode`
- **Schema Export**: `export_schema`, `export_subject`, `export_context`, `export_global`

### **📦 Available Resources**
- **`registry://status`**: Real-time Schema Registry connection status
- **`registry://info`**: Detailed server configuration and capabilities

### **Claude Desktop Usage Examples**
With the MCP server connected to Claude Desktop, you can use natural language:

```
"List all schema contexts"
"Show me the subjects in the production context"
"Register a new user schema with fields for id, name, and email"
"Export all schemas from the staging context in Avro IDL format"
"Check if my updated schema is compatible with the latest version"
"Get the current configuration for the user-events subject"
```

**📖 Complete Tool Documentation**: [API Reference](docs/api-reference.md)

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

The project includes comprehensive test suites for both single-registry and multi-registry configurations.

#### Single-Registry Tests

```bash
# Start single-registry test environment
./start_test_environment.sh 

# Run comprehensive single-registry tests
./tests/run_comprehensive_tests.sh

# Run specific test categories
./tests/run_comprehensive_tests.sh --basic
./tests/run_comprehensive_tests.sh --workflows

# Stop single-registry test environment
./stop_test_environment.sh 
```

#### Multi-Registry Tests

```bash
# Start multi-registry test environment  
cd tests/
./start_multi_registry_environment.sh

# Run multi-registry integration tests
./run_multi_registry_tests.sh

# Run schema migration tests
./run_migration_tests.sh

# Run batch cleanup tests
./run_multi_registry_batch_cleanup_tests.sh

# Stop multi-registry environment
./stop_multi_registry_environment.sh
```

## 🚀 Production Deployment

Production-ready with pre-built DockerHub images and comprehensive deployment options:

```bash
# Quick production start with pre-built images
docker-compose up -d

# Or direct Docker usage with stable tag
docker run -d -p 38000:8000 aywengo/kafka-schema-reg-mcp:stable

# Or with latest tag
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

## 🎉 Production Ready - True MCP Implementation

**✅ COMPLETE TRANSFORMATION SUCCESS**: Successfully converted from REST API to true MCP protocol server compatible with Claude Desktop and other MCP clients.

**🤖 MCP Features Verified**:
- ✅ **20 MCP Tools** - All schema operations available via natural language
- ✅ **Context Management** - Production/staging environment isolation  
- ✅ **Schema Evolution** - Compatibility testing and version control
- ✅ **Export System** - JSON, Avro IDL formats for backup/migration
- ✅ **Configuration Control** - Global and per-context compatibility settings
- ✅ **Mode Management** - READWRITE/READONLY operational control

**🔧 Claude Desktop Integration**:
```
"List all schema contexts"
"Register a new user schema with fields for id, name, and email" 
"Export all schemas from the production context in Avro IDL format"
"Check if my updated schema is compatible with the latest version"
```

**🧪 Testing Results**: All advanced features tested and working with live Schema Registry including context isolation, schema registration, compatibility checking, configuration management, and export functionality.

**📈 Evolution**: v1.3.0 (True MCP) → v1.2.0 (Configuration) → v1.1.0 (Contexts) → v1.0.0 (REST API)