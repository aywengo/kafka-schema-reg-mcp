# Kafka Schema Registry MCP Server

A comprehensive **Model Context Protocol (MCP) server** that provides Claude Desktop and other MCP clients with advanced tools for Kafka Schema Registry operations. Enterprise-ready with multi-registry support, authentication, and production safety features.

## 🎯 Why Use This MCP?

Transform your schema management workflow with AI-powered automation:
- **Natural Language Operations**: "Migrate schemas from dev to prod" or "Export all schemas in staging context"
- **Multi-Environment Management**: Handle development, staging, and production registries simultaneously
- **Production Safety**: Built-in viewonly modes and granular permissions
- **Enterprise Features**: Schema contexts, batch operations, and comprehensive export capabilities

## ✨ Key Features

### **🤖 AI-First Design**
- **48 MCP Tools**: Complete schema operations via natural language with Claude Desktop
- **Real-Time Progress**: Monitor long-running operations with live progress tracking
- **Multi-Registry Support**: Manage up to 8 Schema Registry instances simultaneously
- **Context-Aware**: Logical schema grouping for environment isolation

### **🏢 Enterprise Ready**
- **Authentication & Authorization**: OAuth2 with role-based access control
- **Production Safety**: Per-registry viewonly modes and operational controls
- **Schema Migration**: Advanced tools for cross-registry and cross-context migration
- **Comprehensive Export**: JSON, Avro IDL formats for backup and documentation

### **⚙️ Advanced Capabilities**
- **Schema Contexts**: Logical grouping for multi-tenancy and environment isolation
- **Configuration Management**: Global and per-subject compatibility controls
- **Mode Control**: READWRITE, READONLY, IMPORT operational states
- **Cross-Registry Operations**: Compare, migrate, and synchronize schemas

## 🚀 Quick Start

### Option 1: Docker (Recommended)
```bash
# Pull the stable image
docker pull aywengo/kafka-schema-reg-mcp:stable

# Configure Claude Desktop
{
  "mcpServers": {
    "kafka-schema-registry": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "SCHEMA_REGISTRY_URL",
        "-e", "SCHEMA_REGISTRY_USER", 
        "-e", "SCHEMA_REGISTRY_PASSWORD",
        "-e", "VIEWONLY",
        "aywengo/kafka-schema-reg-mcp:stable"
      ],
      "env": {
        "SCHEMA_REGISTRY_URL": "http://localhost:8081",
        "VIEWONLY": "false"
      }
    }
  }
}
```

### Option 2: Multi-Registry Setup
```bash
# Configure multiple registries
{
  "mcpServers": {
    "kafka-schema-registry-multi": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "SCHEMA_REGISTRY_NAME_1",
        "-e", "SCHEMA_REGISTRY_URL_1",
        "-e", "VIEWONLY_1",
        "-e", "SCHEMA_REGISTRY_NAME_2", 
        "-e", "SCHEMA_REGISTRY_URL_2",
        "-e", "VIEWONLY_2",
        "aywengo/kafka-schema-reg-mcp:stable"
      ],
      "env": {
        "SCHEMA_REGISTRY_NAME_1": "development",
        "SCHEMA_REGISTRY_URL_1": "http://dev-registry:8081",
        "VIEWONLY_1": "false",
        "SCHEMA_REGISTRY_NAME_2": "production",
        "SCHEMA_REGISTRY_URL_2": "http://prod-registry:8081", 
        "VIEWONLY_2": "true"
      }
    }
  }
}
```

## 💬 Example Claude Conversations

Once configured, you can use natural language with Claude:

**Single Registry:**
- "List all schema contexts"
- "Register a user schema with id, name, and email fields"
- "Export all schemas from the production context"
- "Check compatibility of my updated schema"

**Multi-Registry:**
- "Show me all my Schema Registry instances"
- "Compare schemas between development and production"
- "Migrate user-events schema from staging to production"
- "Test connections to all registries"

## 🔧 Available Tools

**Schema Management (8 tools):**
- Register, retrieve, and manage Avro schemas
- Version control with compatibility checking
- Subject management and deletion

**Context Management (4 tools):**
- Create and manage schema contexts for environment isolation
- List contexts with detailed information

**Configuration Management (8 tools):**
- Global and per-subject compatibility settings
- Operational mode control (READWRITE/READONLY/IMPORT)

**Multi-Registry Operations (12 tools):**
- Cross-registry schema comparison and migration
- Batch operations and task management
- Registry connection testing and monitoring

**Export & Analysis (16 tools):**
- Comprehensive export in multiple formats
- Schema statistics and analysis
- Progress tracking for long-running operations

## 🏗️ Architecture

- **Unified Server Design**: Auto-detects single vs multi-registry mode
- **MCP Protocol**: Uses official MCP Python SDK with JSON-RPC over stdio
- **Enterprise Integration**: Supports authentication, authorization, and audit trails
- **Production Deployment**: Docker images for AMD64 and ARM64 architectures

## 📚 Documentation & Support

- **Complete Documentation**: [GitHub Repository](https://github.com/aywengo/kafka-schema-reg-mcp)
- **Configuration Examples**: Pre-built Claude Desktop configurations
- **API Reference**: Detailed tool documentation and examples
- **Docker Hub**: [aywengo/kafka-schema-reg-mcp](https://hub.docker.com/r/aywengo/kafka-schema-reg-mcp)

## 🔐 Security & Production

- **OAuth2 Authentication**: Role-based access with read/write/admin scopes
- **Production Safety**: Viewonly modes prevent accidental modifications
- **Secure Configuration**: Environment variable-based configuration
- **Multi-Architecture**: AMD64 and ARM64 Docker images available

## 🎯 Perfect For

- **DevOps Teams**: Managing schemas across multiple environments
- **Data Engineers**: Schema evolution and compatibility testing
- **Platform Teams**: Multi-tenant schema governance
- **AI-First Workflows**: Natural language schema operations with Claude

---

**Get Started**: Clone from [GitHub](https://github.com/aywengo/kafka-schema-reg-mcp) or pull from [Docker Hub](https://hub.docker.com/r/aywengo/kafka-schema-reg-mcp)

**Version**: 1.7.0 | **License**: MIT | **Maintained**: Active Development 