# Kafka Schema Registry MCP Server

A comprehensive **Message Control Protocol (MCP) server** that provide
s Claude Desktop and other MCP clients with tools for Kafka Schema Registry operations. Features include advanced **Schema Context** support for logical schema grouping, **Configuration Management** for compatibility settings, **Mode Control** for operational state management, and **comprehensive Schema Export** capabilities for backup, migration, and schema documentation.

<table width="100%">
<tr>
<td width="33%" style="vertical-align: top;">
<div style="background-color: white; padding: 20px; border-radius: 10px;">
  <img src="docs/logo_400_mcp_kafka_schema_reg.png" alt="Kafka Schema Registry MCP Logo" width="100%">
</div>
</td>
<td width="67%" style="vertical-align: top; padding-left: 20px;">

> **🎯 True MCP Implementation**: This server uses the official MCP Python SDK and communicates via JSON-RPC over stdio, making it fully compatible with Claude Desktop and other MCP clients.
</td>
</tr>
</table>

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

### 📋 MCP Features
- ✅ **48 MCP Tools**: Complete schema operations via natural language
- ✅ **Async Task Management**: Non-blocking operations with ThreadPoolExecutor
- ✅ **Real-Time Progress Tracking**: Monitor long-running operations (0-100%)
- ✅ **Task Lifecycle Control**: Create, monitor, cancel operations
- ✅ **Multi-Registry Support**: Manage up to 8 Schema Registry instances
- ✅ **Numbered Environment Config**: Clean `SCHEMA_REGISTRY_NAME_X`, `SCHEMA_REGISTRY_URL_X` pattern
- ✅ **Per-Registry READONLY**: Independent `READONLY_X` mode control
- ✅ **Cross-Registry Operations**: Compare, migrate, and sync schemas
- ✅ **Context Management**: Production/staging environment isolation  
- ✅ **Schema Evolution**: Compatibility testing and version control
- ✅ **Export System**: JSON, Avro IDL formats for backup/migration
- ✅ **Configuration Control**: Global and per-context compatibility settings
- ✅ **Claude Desktop Ready**: Direct integration with AI workflows
- ✅ **Multi-Platform Support**: AMD64 and ARM64 architectures
- ✅ **Stable Tag**: Use `:stable` for production deployments
- ✅ **Schema Statistics**: Comprehensive counting and analysis tools for contexts, schemas, and versions

## 🏗️ Architecture

- **Unified Server Design**: Single `kafka_schema_registry_unified_mcp.py` that auto-detects single vs multi-registry mode
- **MCP Protocol Server**: Uses official MCP Python SDK with JSON-RPC over stdio
- **Kafka Schema Registry Integration**: Backend for schema storage and management  
- **KRaft Mode Support**: Works with modern Kafka without Zookeeper dependency
- **Context-Aware Operations**: All tools support optional context parameters
- **Claude Desktop Integration**: Direct integration with Claude Desktop via MCP configuration
- **Enterprise-Ready**: Granular control over compatibility and operational modes
- **Multi-Format Export**: JSON and Avro IDL export formats through MCP tools
- **Backward Compatibility**: 100% compatible with existing single-registry configurations

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

#### Step 3: Run the Unified Server
```bash
# The unified server automatically detects single vs multi-registry mode
python kafka_schema_registry_unified_mcp.py
```

#### Step 4: Test with Complete Test Suite
```bash
# Run the unified test runner (starts environment + runs all tests)
cd tests
./run_all_tests.sh

# Or run essential tests only (faster)
./run_all_tests.sh --quick

# Or use the simple wrapper
./test-unified.sh
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

## 💬 MCP Prompts & Guided Workflows

The MCP server includes **8 comprehensive prompts** that provide guided workflows and best practices for schema management. These prompts appear in Claude Desktop to help you learn and execute complex operations.

### **🚀 Available Prompts**

| Prompt | Purpose | Best For |
|---------|---------|----------|
| **`schema-getting-started`** | Introduction to basic operations | New users, onboarding |
| **`schema-registration`** | Complete guide for registering schemas | Developers, schema creation |
| **`context-management`** | Organizing schemas by environment/team | DevOps, multi-environment setups |
| **`schema-export`** | Export for backup, docs, compliance | Documentation, backup procedures |
| **`multi-registry`** | Managing multiple registries | Multi-environment, disaster recovery |
| **`schema-compatibility`** | Safe schema evolution | Schema changes, production safety |
| **`troubleshooting`** | Diagnose and resolve issues | Problem resolution, debugging |
| **`advanced-workflows`** | Enterprise patterns and automation | Complex deployments, team coordination |

### **🎮 How to Use Prompts**

#### In Claude Desktop:
```
Human: Show me the schema-getting-started prompt

Claude: [Displays comprehensive getting started guide with examples]
```

```
Human: I need help with schema compatibility

Claude: Let me show you the schema-compatibility prompt which covers compatibility levels, safe vs breaking changes, and evolution workflows.
```

#### **Learning Path Recommendations:**

**🔰 Beginner Path** (15-30 minutes):
1. `schema-getting-started` - Understand basics
2. `schema-registration` - Register your first schema  
3. `context-management` - Organize with contexts

**⚡ Intermediate Path** (30-60 minutes):
4. `schema-export` - Document and backup
5. `schema-compatibility` - Safe evolution
6. `troubleshooting` - Handle common issues

**🚀 Advanced Path** (1-2 hours):
7. `multi-registry` - Multi-environment management
8. `advanced-workflows` - Enterprise patterns

### **📋 Prompt Features**

- **🎯 Actionable Commands**: Direct copy-paste examples for immediate use
- **📖 Step-by-Step Workflows**: Guided processes for complex operations
- **🏢 Enterprise Patterns**: Real-world scenarios and best practices
- **🔗 Cross-References**: Connections between related prompts and tools
- **📊 Use Case Examples**: Concrete scenarios for different industries

### **🛠️ Role-Based Recommendations**

| Role | Recommended Prompts |
|------|-------------------|
| **Developers** | `schema-registration`, `schema-compatibility` |
| **DevOps Engineers** | `multi-registry`, `advanced-workflows` |
| **Data Engineers** | `schema-export`, `context-management` |
| **System Administrators** | `troubleshooting`, `multi-registry` |

**📖 Complete Prompts Guide**: [MCP Prompts Documentation](docs/prompts-guide.md)

## 🎯 Key Capabilities

### **📦 Schema Export System**
Comprehensive export functionality with 17 endpoints supporting backup, migration, and documentation:
- **Multiple Formats**: JSON, Avro IDL, ZIP bundles
- **Flexible Scopes**: Single schemas, subjects, contexts, or global exports
- **Use Cases**: Environment promotion, disaster recovery, compliance auditing, documentation generation

**📖 Detailed Guide**: [API Reference - Export Endpoints](docs/api-reference.md#export-endpoints)

### **🔄 Schema Migration Capabilities**
Advanced migration tools for moving schemas between registries and contexts:

#### Context Migration (Docker-Based)
The `migrate_context` tool now generates Docker configuration files for the [kafka-schema-reg-migrator](https://github.com/aywengo/kafka-schema-reg-migrator):
- **Better Error Handling**: Robust error recovery and retry mechanisms
- **Scalable**: Handles large-scale migrations efficiently
- **Progress Monitoring**: Real-time progress tracking and logging
- **Configuration Review**: Preview before execution

**Example:**
```
Human: "Migrate all schemas from development context to production"

Claude: I'll generate the migration configuration for you.

[Uses migrate_context MCP tool]
📋 Migration configuration generated:
   - .env file with registry credentials
   - docker-compose.yml for the migrator
   - migrate-context.sh execution script
   
To run: Save files and execute ./migrate-context.sh
```

#### Direct Schema Migration
Individual schemas can be migrated directly using `migrate_schema`:
- **Version Control**: Migrate specific versions or all versions
- **ID Preservation**: Maintain schema IDs using IMPORT mode
- **Compatibility Checking**: Ensure schema compatibility

**📖 Migration Guide**: [MCP Tools Reference - Migration](docs/mcp-tools-reference.md#29-migrate_context)

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

## 🔑 Authentication Overview

There are two types of authentication in this project:

1. **Schema Registry Authentication** (Backend):
   - Controls how the MCP server connects to your Kafka Schema Registry instances.
   - Set via `SCHEMA_REGISTRY_USER`, `SCHEMA_REGISTRY_PASSWORD` (and their multi-registry variants).
   - These credentials are NOT used to authenticate users of the MCP server itself.

2. **MCP Server Authentication** (Frontend):
   - Controls who can access the MCP server and its tools.
   - Enable with `ENABLE_AUTH=true` and configure via `AUTH_ISSUER_URL`, `AUTH_VALID_SCOPES`, etc.
   - This is optional and defaults to open access if not set.

> **Note:** Setting `SCHEMA_REGISTRY_USER`/`PASSWORD` only protects the connection to the backend registry, not the MCP server API/tools. To secure the MCP server itself, use the `ENABLE_AUTH` and related variables.

## 🔐 Authentication

> **There are two layers of authentication:**
>
> - **Schema Registry Auth**: Controls how the MCP server connects to the backend registry. Set `SCHEMA_REGISTRY_USER`/`PASSWORD` (and `_X` variants for multi-registry) for this purpose.
> - **MCP Server Auth**: Controls who can access the MCP server and its tools. Use `ENABLE_AUTH` and related `AUTH_*` variables to secure the MCP server itself.

**To secure the MCP server itself, you must set `ENABLE_AUTH=true` and configure the OAuth2 variables.**

### Environment Variables (Authentication & Authorization)

| Variable | Description | Default | Applies To |
|----------|-------------|---------|------------|
| `SCHEMA_REGISTRY_USER` | Username for backend Schema Registry | *(empty)* | Schema Registry (backend) |
| `SCHEMA_REGISTRY_PASSWORD` | Password for backend Schema Registry | *(empty)* | Schema Registry (backend) |
| `SCHEMA_REGISTRY_USER_X` | Username for multi-registry backend | *(empty)* | Schema Registry (backend) |
| `SCHEMA_REGISTRY_PASSWORD_X` | Password for multi-registry backend | *(empty)* | Schema Registry (backend) |
| `ENABLE_AUTH` | Enable OAuth2 authentication/authorization | `false` | MCP Server (frontend) |
| `AUTH_ISSUER_URL` | OAuth2 issuer URL | `https://example.com` | MCP Server (frontend) |
| `AUTH_VALID_SCOPES` | Comma-separated list of valid scopes | `myscope` | MCP Server (frontend) |
| `AUTH_DEFAULT_SCOPES` | Comma-separated list of default scopes | `myscope` | MCP Server (frontend) |
| `AUTH_REQUIRED_SCOPES` | Comma-separated list of required scopes | `myscope` | MCP Server (frontend) |
| `AUTH_CLIENT_REG_ENABLED` | Enable dynamic client registration | `true` | MCP Server (frontend) |
| `AUTH_REVOCATION_ENABLED` | Enable token revocation endpoint | `true` | MCP Server (frontend) |

## 🔐 OAuth Scopes & Authorization

The MCP server implements a three-tier permission system when OAuth authentication is enabled (`ENABLE_AUTH=true`):

### **🎯 Permission Scopes**

| Scope | Permissions | Description |
|-------|-------------|-------------|
| **`read`** | View schemas, subjects, configurations | Basic read-only access to all schema information |
| **`write`** | Register schemas, update configs (includes `read`) | Schema modification and configuration management |
| **`admin`** | Delete subjects, manage registries (includes `write` + `read`) | Full administrative access |

### **🛠️ Tool-Level Authorization**

All MCP tools are protected by scopes:

#### Read Scope (`read`) — View/Export/Status Operations
- `list_registries`, `get_registry_info`, `test_registry_connection`, `test_all_registries`
- `compare_registries`, `compare_contexts_across_registries`, `find_missing_schemas`
- `get_schema`, `get_schema_versions`, `list_subjects`, `check_compatibility`
- `get_global_config`, `get_subject_config`
- `get_mode`, `get_subject_mode`
- `list_contexts`
- `export_schema`, `export_subject`, `export_context`, `export_global`
- `list_migrations`, `get_migration_status`
- `count_contexts`, `count_schemas`, `count_schema_versions`, `get_registry_statistics`
- `get_task_status`, `get_task_progress`, `list_active_tasks`, `list_statistics_tasks`, `get_statistics_task_progress`
- `get_default_registry`, `check_readonly_mode`, `get_oauth_scopes_info`, `get_operation_info_tool`

#### Write Scope (`write`) — Modification Operations
- `register_schema`
- `update_global_config`, `update_subject_config`
- `update_mode`, `update_subject_mode`
- `create_context`

#### Admin Scope (`admin`) — Administrative/Cleanup Operations
- `delete_context`, `delete_subject`
- `migrate_schema`, `migrate_context`
- `clear_context_batch`, `clear_multiple_contexts_batch`
- `set_default_registry`, `cancel_task`

> **Note:** The `get_oauth_scopes_info` tool will show the enforced required scopes for every tool, as defined in the code. Use it to audit or discover permissions for any operation.

### **🧪 Development Testing**

For development and testing, you can use special development tokens:

```bash
# Format: dev-token-{scopes}
export OAUTH_TOKEN="dev-token-read,write,admin"  # Full access
export OAUTH_TOKEN="dev-token-read"              # Read-only access  
export OAUTH_TOKEN="dev-token-write"             # Read + Write access
```

### **🔧 OAuth Configuration Examples**

#### Development Environment (Permissive)
```bash
export ENABLE_AUTH=true
export AUTH_ISSUER_URL="https://dev-auth.example.com"
export AUTH_VALID_SCOPES="read,write,admin"
export AUTH_DEFAULT_SCOPES="read"
export AUTH_REQUIRED_SCOPES="read"
```

#### Production Environment (Restrictive)
```bash
export ENABLE_AUTH=true
export AUTH_ISSUER_URL="https://prod-auth.example.com"  
export AUTH_VALID_SCOPES="read,write"
export AUTH_DEFAULT_SCOPES="read"
export AUTH_REQUIRED_SCOPES="read,write"
```

#### Read-Only Environment (Analytics/Monitoring)
```bash
export ENABLE_AUTH=true
export AUTH_ISSUER_URL="https://auth.example.com"
export AUTH_VALID_SCOPES="read"
export AUTH_DEFAULT_SCOPES="read"
export AUTH_REQUIRED_SCOPES="read"
```

### **📋 Scope Information Tool**

Use the `get_oauth_scopes_info` MCP tool to discover:
- Available scopes and their permissions
- Required scopes for each tool
- Development token formats
- Current authentication configuration

**Example usage with Claude:**
```
"Show me the OAuth scopes and which tools require which permissions"
"What development tokens can I use for testing?"
"Which tools require admin access?"
```

### **🛡️ Security Best Practices**

1. **Principle of Least Privilege**: Grant only the minimum scopes needed
2. **Environment Separation**: Use different scope configurations per environment  
3. **Read-Only Production**: Consider read-only scopes for production monitoring
4. **Development Tokens**: Only use `dev-token-*` formats in development environments
5. **Token Rotation**: Implement regular token rotation in production

### **🚨 Security Vulnerability Management**

The project includes automated security scanning via GitHub Actions, with documented handling of security exceptions:

#### Security Scanning
- **Trivy**: Container vulnerability scanning for critical, high, and medium severity issues
- **Safety & pip-audit**: Python dependency vulnerability scanning
- **TruffleHog**: Secrets detection in code and git history
- **Docker Bench Security**: Docker configuration security assessment

#### Security Exception Handling
Some vulnerabilities may be marked as "will_not_fix" by upstream maintainers when they:
- Are not exploitable in normal usage scenarios
- Would break compatibility if fixed
- Have no available fixes from the package maintainers

**Documented Exceptions:**
- All security exceptions are documented in `.trivyignore` with detailed rationale
- Each exception includes CVE reference, status explanation, and risk assessment
- Regular review process ensures exceptions remain valid

**Current Exceptions:**
- `CVE-2023-45853` (zlib): Integer overflow in zipOpenNewFileInZip4_6 function
  - Status: will_not_fix by Debian maintainers
  - Impact: Function not used in application context
  - Risk: Low - not exploitable in our use case

#### Security Configuration
```bash
# Disable VEX notices (already documented)
export TRIVY_DISABLE_VEX_NOTICE=true
```

The security scan workflow continues to monitor for new vulnerabilities while allowing documented exceptions to avoid false positives in CI/CD pipelines.

## 🧪 Testing

The project includes a unified, comprehensive test suite with automatic environment management.

#### Unified Test Runner (Recommended)

```bash
# Run complete test suite with automatic environment management
cd tests/
./run_all_tests.sh

# Or run essential tests only (faster)
./run_all_tests.sh --quick

# Keep environment running for debugging
./run_all_tests.sh --no-cleanup

# Show all available options
./run_all_tests.sh --help
```

#### Manual Environment Management

```bash
# Start unified environment (supports both single and multi-registry tests)
cd tests/
./start_test_environment.sh multi

# Run individual tests
python3 test_basic_server.py
python3 test_multi_registry_mcp.py

# Stop environment
./stop_test_environment.sh clean
```

#### Environment Mode Options

```bash
# Start only DEV registry (single-registry tests)
./start_test_environment.sh dev

# Start full environment (multi-registry tests)  
./start_test_environment.sh multi

# Start with UI monitoring
./start_test_environment.sh ui
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

## 🆕 What's New in v1.8.x

- **Optional OAuth2 Authentication & Authorization**: Enable with `ENABLE_AUTH=true` and configure via environment variables:
  - `AUTH_ISSUER_URL`, `AUTH_VALID_SCOPES`, `AUTH_DEFAULT_SCOPES`, `AUTH_REQUIRED_SCOPES`, `AUTH_CLIENT_REG_ENABLED`, `AUTH_REVOCATION_ENABLED`
- **Configurable AuthSettings**: All OAuth2 settings are now configurable via environment variables for both single and multi-registry modes.
- **Unit Tests for Auth Config**: Added tests for both single and multi-registry auth configuration.
- **Upgraded MCP SDK**: Now using `mcp[cli]==1.9.2` with full authorization support.
- **Schema Statistics & Counting**: New tools for monitoring registry usage:
  - `count_contexts`: Track context distribution
  - `count_schemas`: Monitor schema growth
  - `count_schema_versions`: Track schema evolution
  - `get_registry_statistics`: Comprehensive registry analytics
  [📖 Details](docs/mcp-tools-reference.md#schema-statistics-and-counting-tools)

### Environment Variables (Authentication & Authorization)

| Variable | Description | Default |
|----------|-------------|---------|
| `ENABLE_AUTH` | Enable OAuth2 authentication/authorization | `false` |
| `AUTH_ISSUER_URL` | OAuth2 issuer URL | `https://example.com` |
| `AUTH_VALID_SCOPES` | Comma-separated list of valid scopes | `myscope` |
| `AUTH_DEFAULT_SCOPES` | Comma-separated list of default scopes | `myscope` |
| `AUTH_REQUIRED_SCOPES` | Comma-separated list of required scopes | `myscope` |
| `AUTH_CLIENT_REG_ENABLED` | Enable dynamic client registration | `true` |
| `AUTH_REVOCATION_ENABLED` | Enable token revocation endpoint | `true` |

**Example usage:**
```bash
export ENABLE_AUTH=true
export AUTH_ISSUER_URL="https://auth.example.com"
export AUTH_VALID_SCOPES="myscope,otherscope"
export AUTH_DEFAULT_SCOPES="myscope"
export AUTH_REQUIRED_SCOPES="myscope"
export AUTH_CLIENT_REG_ENABLED=true
export AUTH_REVOCATION_ENABLED=true
```

- If `ENABLE_AUTH` is not set or is false, the server runs with no authentication (backward compatible).
- All settings apply to both single and multi-registry modes.

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