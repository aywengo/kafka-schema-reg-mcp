[![Verified on MseeP](https://mseep.ai/badge.svg)](https://mseep.ai/app/2978f264-313d-4181-b592-145879b471b1)

# Kafka Schema Registry MCP Server

A comprehensive **Message Control Protocol (MCP) server** that provides Claude Desktop and other MCP clients with tools for Kafka Schema Registry operations. Features advanced schema context support, multi-registry management, and comprehensive schema export capabilities.

<table width="100%">
<tr>
<td width="33%" style="vertical-align: top;">
<div style="background-color: white; padding: 20px; border-radius: 10px;">
  <img src="docs/logo_400_mcp_kafka_schema_reg.png" alt="Kafka Schema Registry MCP Logo" width="100%">
</div>
</td>
<td width="67%" style="vertical-align: top; padding-left: 20px;">

> **🎯 True MCP Implementation**: Uses modern **FastMCP 2.8.0+ framework** with full **MCP 2025-06-18 specification compliance**. Fully compatible with Claude Desktop and other MCP clients using JSON-RPC over stdio.

**Latest Version:** [v2.0.2](CHANGELOG.md) | **Docker:** `aywengo/kafka-schema-reg-mcp:stable`
</td>
</tr>
</table>

## 📋 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [✨ Key Features](#-key-features)
- [📦 Installation](#-installation)
- [⚙️ Configuration](#️-configuration)
- [💬 Usage Examples](#-usage-examples)
- [🔒 Authentication & Security](#-authentication--security)
- [📚 Documentation](#-documentation)
- [🧪 Testing](#-testing)
- [🚀 Deployment](#-deployment)
- [🤝 Contributing](#-contributing)
- [🆕 What's New](#-whats-new)

## 🚀 Quick Start

### 1. Run with Docker (Recommended)
```bash
# Latest stable release
docker pull aywengo/kafka-schema-reg-mcp:stable
docker run -e SCHEMA_REGISTRY_URL=http://localhost:8081 aywengo/kafka-schema-reg-mcp:stable
```

### 2. Configure Claude Desktop
Copy a ready-to-use configuration from [`config-examples/`](config-examples/):

```bash
# macOS
cp config-examples/claude_desktop_stable_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Linux  
cp config-examples/claude_desktop_stable_config.json ~/.config/claude-desktop/config.json
```

### 3. Start Using with Claude
Restart Claude Desktop and try these prompts:
- *"List all schema contexts"*
- *"Show me the subjects in the production context"* 
- *"Register a new user schema with fields for id, name, and email"*

## ✨ Key Features

- **🤖 Claude Desktop Integration** - Direct MCP integration with natural language interface
- **🏢 Multi-Registry Support** - Manage up to 8 Schema Registry instances simultaneously
- **📋 Schema Contexts** - Logical grouping for production/staging environment isolation
- **🔄 Schema Migration** - Cross-registry migration with backup and verification
- **📊 Comprehensive Export** - JSON, Avro IDL formats for backup and documentation
- **🔒 Production Safety** - READONLY mode and per-registry access control
- **🔐 OAuth 2.1 Authentication** - Enterprise-grade security with scope-based permissions
- **📈 Real-time Progress** - Async operations with progress tracking and cancellation
- **🔗 Resource Linking** - HATEOAS navigation with enhanced tool responses
- **🧪 Full MCP Compliance** - 48+ tools following MCP 2025-06-18 specification

> **📖 See detailed feature descriptions**: [docs/api-reference.md](docs/api-reference.md)

## 📦 Installation

### Option A: Docker (Recommended)
```bash
# Production stable
docker pull aywengo/kafka-schema-reg-mcp:stable

# Latest development  
docker pull aywengo/kafka-schema-reg-mcp:latest

# Specific version
docker pull aywengo/kafka-schema-reg-mcp:2.0.2
```

### Option B: Local Python
```bash
git clone https://github.com/aywengo/kafka-schema-reg-mcp
cd kafka-schema-reg-mcp
pip install -r requirements.txt
python kafka_schema_registry_unified_mcp.py
```

### Option C: Docker Compose
```bash
docker-compose up -d  # Includes Schema Registry for testing
```

> **📖 Detailed installation guide**: [docs/deployment.md](docs/deployment.md)

## ⚙️ Configuration

### Single Registry Mode
```bash
export SCHEMA_REGISTRY_URL="http://localhost:8081"
export SCHEMA_REGISTRY_USER=""           # Optional
export SCHEMA_REGISTRY_PASSWORD=""       # Optional
export READONLY="false"                  # Production safety
```

### Multi-Registry Mode (Up to 8 Registries)
```bash
# Development Registry
export SCHEMA_REGISTRY_NAME_1="development"
export SCHEMA_REGISTRY_URL_1="http://dev-registry:8081"
export READONLY_1="false"

# Production Registry (with safety)
export SCHEMA_REGISTRY_NAME_2="production"  
export SCHEMA_REGISTRY_URL_2="http://prod-registry:8081"
export READONLY_2="true"                     # Read-only protection
```

### Claude Desktop Configuration
Pre-configured examples available in [`config-examples/`](config-examples/):

| Configuration | Use Case | File |
|---------------|----------|------|
| **Production** | Stable Docker deployment | [`claude_desktop_stable_config.json`](config-examples/claude_desktop_stable_config.json) |
| **Multi-Environment** | DEV/STAGING/PROD registries | [`claude_desktop_multi_registry_docker.json`](config-examples/claude_desktop_multi_registry_docker.json) |
| **Local Development** | Python local execution | [`claude_desktop_config.json`](config-examples/claude_desktop_config.json) |
| **Read-Only Safety** | Production with safety | [`claude_desktop_readonly_config.json`](config-examples/claude_desktop_readonly_config.json) |

> **📖 Complete configuration guide**: [config-examples/README.md](config-examples/README.md)

## 💬 Usage Examples

### Schema Management
```bash
# In Claude Desktop, use natural language:
"Register a user schema with id, name, email fields"
"Check if my updated schema is compatible"
"Export all schemas from staging context"
"List subjects in production context"
```

### Multi-Registry Operations  
```bash
"Compare development and production registries"
"Migrate user-events schema from staging to production"
"Test connections to all registries"
"Show me registry statistics"
```

### Batch Operations
```bash
"Clear all schemas from test context"
"Export global schemas for backup"
"Count schemas across all contexts"
```

> **📖 More examples**: [examples/](examples/) | **📖 Use cases**: [docs/use-cases.md](docs/use-cases.md)

## 🔒 Authentication & Security

### OAuth 2.1 Support (Optional)
```bash
# Enable authentication
export ENABLE_AUTH=true
export AUTH_ISSUER_URL="https://your-oauth-provider.com"
export AUTH_AUDIENCE="your-client-id"
```

**Supported Providers:** Azure AD, Google OAuth, Keycloak, Okta, GitHub

**Permission Scopes:**
- `read` - View schemas, configurations
- `write` - Register schemas, update configs (includes read)
- `admin` - Delete subjects, full control (includes write + read)

### Production Safety Features
- **READONLY Mode** - Prevent accidental changes in production
- **URL Validation** - SSRF protection with configurable localhost access
- **Scope-based Authorization** - Fine-grained tool-level permissions
- **Per-Registry Controls** - Independent safety settings

> **📖 Security guide**: [docs/deployment.md#security](docs/deployment.md#security)

## 📚 Documentation

| Guide | Description |
|-------|-------------|
| **[API Reference](docs/api-reference.md)** | Complete tool documentation with examples |
| **[Use Cases](docs/use-cases.md)** | Real-world scenarios and implementation patterns |
| **[Deployment Guide](docs/deployment.md)** | Docker, Kubernetes, cloud platforms, CI/CD |
| **[IDE Integration](docs/ide-integration.md)** | VS Code, Claude Code, Cursor setup |
| **[Configuration Examples](config-examples/)** | Ready-to-use Claude Desktop configs |
| **[Testing Guide](TESTING_SETUP_GUIDE.md)** | Comprehensive testing setup |
| **[Changelog](CHANGELOG.md)** | Version history and migration notes |
| **[v2.0.0 Highlights](README-v2.0.0-HIGHLIGHTS.md)** | Major version features |

### Additional Resources
- **[Examples](examples/)** - Usage examples and code samples
- **[Scripts](scripts/)** - Utility scripts and automation
- **[Helm Charts](helm/)** - Kubernetes deployment
- **[Tests](tests/)** - Test suites and validation

## 🧪 Testing

### Quick Test
```bash
cd tests/
./run_all_tests.sh --quick    # Essential tests
./run_all_tests.sh           # Complete test suite
```

### Docker Testing
```bash
python tests/test_docker_mcp.py
```

> **📖 Testing guide**: [TESTING_SETUP_GUIDE.md](TESTING_SETUP_GUIDE.md)

## 🚀 Deployment

### Production Docker
```bash
# With docker-compose
docker-compose up -d

# Direct Docker  
docker run -d -p 38000:8000 \
  -e SCHEMA_REGISTRY_URL=http://registry:8081 \
  aywengo/kafka-schema-reg-mcp:stable
```

### Kubernetes
```bash
# Using Helm charts
helm install kafka-schema-mcp ./helm/kafka-schema-reg-mcp
```

> **📖 Deployment guide**: [docs/deployment.md](docs/deployment.md)

## 🤝 Contributing

We welcome contributions! Please see:
- **[Contributing Guidelines](.github/CONTRIBUTING.md)** 
- **[Code of Conduct](.github/CODE_OF_CONDUCT.md)**
- **[Development Setup](docs/deployment.md#local-development)**

### Quick Development Setup
```bash
git clone https://github.com/aywengo/kafka-schema-reg-mcp
cd kafka-schema-reg-mcp
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python kafka_schema_registry_unified_mcp.py
```

## 🆕 What's New

### v2.0.2 (Latest)
- **🔒 Security Fixes** - Resolved credential exposure in logging
- **🤖 Interactive Schema Migration** - Smart migration with user preference elicitation
- **💾 Automatic Backups** - Pre-migration backup creation
- **✅ Post-Migration Verification** - Comprehensive schema validation

### v2.0.0 (Major Release)  
- **🚀 FastMCP 2.8.0+ Framework** - Complete architecture upgrade
- **📊 MCP 2025-06-18 Compliance** - Latest protocol specification
- **🔐 OAuth 2.1 Generic Discovery** - Universal provider compatibility
- **🔗 Resource Linking** - HATEOAS navigation in tool responses

> **📖 Full changelog**: [CHANGELOG.md](CHANGELOG.md) | **📖 v2.0.0 features**: [README-v2.0.0-HIGHLIGHTS.md](README-v2.0.0-HIGHLIGHTS.md)

---

<a href="https://glama.ai/mcp/servers/@aywengo/kafka-schema-reg-mcp">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@aywengo/kafka-schema-reg-mcp/badge" />
</a>

---

**🐳 Docker Hub:** [`aywengo/kafka-schema-reg-mcp`](https://hub.docker.com/r/aywengo/kafka-schema-reg-mcp) | **📊 Stats:** 48+ MCP Tools, 8 Registries, OAuth 2.1, Multi-platform

**License:** MIT | **Maintainer:** [@aywengo](https://github.com/aywengo) | **Issues:** [GitHub Issues](https://github.com/aywengo/kafka-schema-reg-mcp/issues)
