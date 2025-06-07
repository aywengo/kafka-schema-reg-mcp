# Kafka Schema Registry MCP Server

A comprehensive **MCP (Model Context Protocol) server** that provides Claude Desktop and other MCP clients with tools for Kafka Schema Registry operations. True MCP implementation using the official SDK with JSON-RPC over stdio.

## ✨ Key Features

- **🤖 Claude Desktop Compatible**: Direct integration via MCP protocol
- **📋 48 MCP Tools**: Complete schema operations via natural language
- **🌐 Multi-Registry Support**: Connect to up to 8 Schema Registry instances
- **⚡ Async Operations**: Non-blocking tasks with real-time progress tracking
- **🔧 Context Management**: Logical grouping with separate "sub-registries"
- **🚀 Simplified Migration**: Ready-to-run Docker commands for context migration
- **🔒 Production Ready**: Per-registry READONLY mode, authentication support
- **📦 Multi-Platform**: AMD64 and ARM64 architectures

## 🚀 Quick Start

### Pull the Image
```bash
# Latest stable release (recommended)
docker pull aywengo/kafka-schema-reg-mcp:stable

# Latest development
docker pull aywengo/kafka-schema-reg-mcp:latest
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
  -e SCHEMA_REGISTRY_NAME_2=production \
  -e SCHEMA_REGISTRY_URL_2=http://prod-registry:8081 \
  -e READONLY_2=true \
  aywengo/kafka-schema-reg-mcp:stable
```

## 🤖 Claude Desktop Integration

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

### Single Registry
```json
{
  "mcpServers": {
    "kafka-schema-registry": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i", "--network", "host",
        "-e", "SCHEMA_REGISTRY_URL",
        "aywengo/kafka-schema-reg-mcp:stable"
      ],
      "env": {
        "SCHEMA_REGISTRY_URL": "http://localhost:8081"
      }
    }
  }
}
```

### Multi-Registry
```json
{
  "mcpServers": {
    "kafka-schema-registry-multi": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i", "--network", "host",
        "-e", "SCHEMA_REGISTRY_NAME_1", "-e", "SCHEMA_REGISTRY_URL_1",
        "-e", "SCHEMA_REGISTRY_NAME_2", "-e", "SCHEMA_REGISTRY_URL_2", "-e", "READONLY_2",
        "aywengo/kafka-schema-reg-mcp:stable"
      ],
      "env": {
        "SCHEMA_REGISTRY_NAME_1": "development",
        "SCHEMA_REGISTRY_URL_1": "http://localhost:8081",
        "SCHEMA_REGISTRY_NAME_2": "production", 
        "SCHEMA_REGISTRY_URL_2": "http://localhost:8082",
        "READONLY_2": "true"
      }
    }
  }
}
```

## 🗣️ Natural Language Usage

With Claude Desktop, use natural language commands:

```
"List all schema contexts"
"Register a user schema with id, name, and email fields"
"Migrate all schemas from staging to production"
"Compare development and production registries"
"Export all schemas from the production context"
"Check if my updated schema is compatible"
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SCHEMA_REGISTRY_URL` | Single registry endpoint | `http://localhost:8081` |
| `SCHEMA_REGISTRY_NAME_X` | Registry alias (X=1-8) | `production` |
| `SCHEMA_REGISTRY_URL_X` | Registry endpoint (X=1-8) | `http://prod:8081` |
| `READONLY_X` | Per-registry readonly (X=1-8) | `true` |
| `SCHEMA_REGISTRY_USER_X` | Username (X=1-8) | `user` |
| `SCHEMA_REGISTRY_PASSWORD_X` | Password (X=1-8) | `pass` |

## 📋 Key MCP Tools

- **Schema Operations**: `register_schema`, `get_schema`, `check_compatibility`
- **Context Management**: `list_contexts`, `create_context`, `migrate_context`
- **Multi-Registry**: `compare_registries`, `migrate_schema`, `test_registry_connection`
- **Configuration**: `update_global_config`, `get_subject_config`
- **Export**: `export_schema`, `export_context`, `export_global`
- **Task Management**: `get_task_progress`, `list_all_active_tasks`

## 🔒 READONLY Mode

Set `READONLY=true` for production safety:
- ✅ **Allowed**: Schema browsing, compatibility checking, exports
- ❌ **Blocked**: Schema registration, deletion, configuration changes

## 🚀 Context Migration

The `migrate_context` tool generates ready-to-run Docker commands using the external [kafka-schema-reg-migrator](https://github.com/aywengo/kafka-schema-reg-migrator):

```
"Migrate staging context to production"
→ Returns: docker run command with automatic credential mapping
→ Features: Copy-paste execution, no file setup required
```

## 📚 Links

- **GitHub**: https://github.com/aywengo/kafka-schema-reg-mcp
- **Documentation**: Full guides and API reference in repository
- **License**: MIT License

---

**Ready to start?** Pull the Docker image and configure Claude Desktop to manage your Kafka Schema Registry with natural language! 🚀 