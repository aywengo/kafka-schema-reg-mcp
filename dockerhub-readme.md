# Kafka Schema Registry MCP Server

A comprehensive **MCP (Model Context Protocol) server** that provides Claude Desktop and other MCP clients with tools for Kafka Schema Registry operations. True MCP implementation using the official SDK with JSON-RPC over stdio.

## ✨ Features

### 🤖 MCP Integration
- **Claude Desktop Compatible**: Direct integration via MCP protocol
- **48 MCP Tools**: Complete schema operations via natural language
- **Multi-Registry Support**: Connect to up to 8 Schema Registry instances
- **Async Task Management**: Non-blocking operations with progress tracking
- **Real-Time Monitoring**: Track long-running operations (0-100%)

### 📋 Schema Management
- **Complete Operations**: Register, retrieve, manage Avro schemas
- **Schema Contexts**: Logical grouping with separate "sub-registries"
- **Version Control**: Handle multiple versions with compatibility checking
- **Cross-Registry Operations**: Compare, migrate, synchronize schemas
- **Configuration Management**: Control compatibility levels globally and per-subject
- **Export System**: JSON, Avro IDL formats for backup/migration

### 🔒 Production Ready
- **Per-Registry READONLY Mode**: Individual readonly protection per registry
- **Authentication Support**: Optional basic auth for Schema Registry
- **Multi-Platform**: AMD64 and ARM64 architectures
- **Enterprise Features**: Context isolation, configuration control, mode management

## 🚀 Quick Start with Docker

### Pull the Image
```bash
# Latest stable release (recommended)
docker pull aywengo/kafka-schema-reg-mcp:stable

# Latest development
docker pull aywengo/kafka-schema-reg-mcp:latest

# Specific version
docker pull aywengo/kafka-schema-reg-mcp:v1.8.1
```

### Single Registry Mode
```bash
docker run -i --rm --network host \
  -e SCHEMA_REGISTRY_URL=http://localhost:8081 \
  aywengo/kafka-schema-reg-mcp:stable
```

### Multi-Registry Mode
```bash
docker run -i --rm --network host \
  -e SCHEMA_REGISTRY_NAME_1=development \
  -e SCHEMA_REGISTRY_URL_1=http://dev-registry:8081 \
  -e READONLY_1=false \
  -e SCHEMA_REGISTRY_NAME_2=production \
  -e SCHEMA_REGISTRY_URL_2=http://prod-registry:8081 \
  -e READONLY_2=true \
  aywengo/kafka-schema-reg-mcp:stable
```

## 🤖 Claude Desktop Integration

### Single Registry Setup
Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "kafka-schema-registry": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i", "--network", "host",
        "-e", "SCHEMA_REGISTRY_URL",
        "-e", "SCHEMA_REGISTRY_USER", 
        "-e", "SCHEMA_REGISTRY_PASSWORD",
        "aywengo/kafka-schema-reg-mcp:stable"
      ],
      "env": {
        "SCHEMA_REGISTRY_URL": "http://localhost:8081",
        "SCHEMA_REGISTRY_USER": "",
        "SCHEMA_REGISTRY_PASSWORD": ""
      }
    }
  }
}
```

### Multi-Registry Setup
```json
{
  "mcpServers": {
    "kafka-schema-registry-multi": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i", "--network", "host",
        "-e", "SCHEMA_REGISTRY_NAME_1", "-e", "SCHEMA_REGISTRY_URL_1", "-e", "READONLY_1",
        "-e", "SCHEMA_REGISTRY_NAME_2", "-e", "SCHEMA_REGISTRY_URL_2", "-e", "READONLY_2",
        "aywengo/kafka-schema-reg-mcp:stable"
      ],
      "env": {
        "SCHEMA_REGISTRY_NAME_1": "development",
        "SCHEMA_REGISTRY_URL_1": "http://localhost:8081",
        "READONLY_1": "false",
        "SCHEMA_REGISTRY_NAME_2": "production", 
        "SCHEMA_REGISTRY_URL_2": "http://localhost:8082",
        "READONLY_2": "true"
      }
    }
  }
}
```

**Configuration Locations:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

## 🔧 Environment Variables

### Single Registry Mode
| Variable | Description | Default |
|----------|-------------|---------|
| `SCHEMA_REGISTRY_URL` | Schema Registry endpoint | `http://localhost:8081` |
| `SCHEMA_REGISTRY_USER` | Username for authentication | *(empty)* |
| `SCHEMA_REGISTRY_PASSWORD` | Password for authentication | *(empty)* |
| `READONLY` | Global read-only mode | `false` |

### Multi-Registry Mode
| Variable | Description | Example |
|----------|-------------|---------|
| `SCHEMA_REGISTRY_NAME_X` | Registry alias (X=1-8) | `production` |
| `SCHEMA_REGISTRY_URL_X` | Registry endpoint (X=1-8) | `http://prod-registry:8081` |
| `SCHEMA_REGISTRY_USER_X` | Username (X=1-8) | `prod-user` |
| `SCHEMA_REGISTRY_PASSWORD_X` | Password (X=1-8) | `prod-password` |
| `READONLY_X` | Per-registry readonly (X=1-8) | `true` |

## 🗣️ Natural Language Usage

With Claude Desktop integration, use natural language commands:

### Single Registry Examples
```
"List all schema contexts"
"Show me the subjects in the production context"
"Register a new user schema with fields for id, name, and email"
"Export all schemas from the staging context"
"Check if my updated schema is compatible with the latest version"
```

### Multi-Registry Examples
```
"List all my Schema Registry instances"
"Compare development and production registries"
"Migrate user-events schema from staging to production"
"Test connections to all registries"
"Register a schema in the development registry"
```

### Async Operations Examples
```
"Migrate all schemas from staging to production"
→ Returns task ID immediately, monitor progress in real-time

"Clean up all feature branch contexts"
→ Executes in parallel with progress tracking

"Compare production and DR registries"
→ Non-blocking comparison with detailed progress updates
```

## 📋 Available MCP Tools

### Core Schema Operations
- `register_schema` - Register new schemas
- `get_schema` - Retrieve schema by ID or subject/version
- `get_schema_versions` - List all versions of a schema
- `check_compatibility` - Test schema compatibility
- `delete_subject` - Remove schema subjects

### Context Management
- `list_contexts` - List all schema contexts
- `create_context` - Create new contexts
- `delete_context` - Remove contexts
- `get_subjects` - List subjects in context

### Multi-Registry Operations
- `list_registries` - Show all configured registries
- `compare_registries` - Compare schemas between registries
- `migrate_schema` - Move schemas between registries
- `migrate_context` - Move entire contexts
- `test_registry_connection` - Verify connectivity

### Configuration & Modes
- `get_global_config` / `update_global_config` - Global compatibility settings
- `get_subject_config` / `update_subject_config` - Per-subject settings
- `get_mode` / `update_mode` - Registry operational modes
- `get_subject_mode` / `update_subject_mode` - Per-subject modes

### Export & Backup
- `export_schema` - Export single schema
- `export_subject` - Export all versions of a subject
- `export_context` - Export entire context
- `export_global` - Export everything

### Task Management
- `get_task_progress` - Monitor operation progress
- `list_all_active_tasks` - View running operations
- `cancel_task` - Stop long-running operations
- `get_migration_progress` - Detailed migration status

## 🔒 READONLY Mode (Production Safety)

When `READONLY=true` is set, the server blocks all modification operations while keeping read and export operations available.

**Blocked Operations:**
- ❌ Schema registration and deletion
- ❌ Context creation and deletion
- ❌ Configuration changes

**Allowed Operations:**
- ✅ Schema browsing and retrieval
- ✅ Compatibility checking (read-only)
- ✅ All export operations

## 🏗️ Architecture

- **Unified Server Design**: Auto-detects single vs multi-registry mode
- **MCP Protocol Server**: Uses official MCP Python SDK with JSON-RPC over stdio
- **Context-Aware Operations**: All tools support optional context parameters
- **Enterprise-Ready**: Granular control over compatibility and operational modes
- **Multi-Format Export**: JSON and Avro IDL export formats

## 🚀 Async Operation Features

- **Task States**: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
- **Progress Tracking**: Human-readable stages with percentage completion
- **Operation Types**: QUICK (<5s), MEDIUM (5-30s), LONG (>30s)
- **Parallel Execution**: Multiple operations run concurrently
- **Graceful Shutdown**: Proper cleanup and task cancellation

## 📚 Documentation & Links

- **GitHub Repository**: https://github.com/aywengo/kafka-schema-reg-mcp
- **Full Documentation**: See README.md in the repository
- **Configuration Examples**: Available in `config-examples/` directory
- **API Reference**: Complete tool documentation available
- **Use Cases**: Enterprise scenarios and examples

## 🆘 Support

- **GitHub Issues**: Report bugs and request features
- **Discussions**: Community support and questions
- **Wiki**: Additional documentation and guides

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Ready to get started?** Pull the Docker image and configure Claude Desktop to begin managing your Kafka Schema Registry with natural language commands! 