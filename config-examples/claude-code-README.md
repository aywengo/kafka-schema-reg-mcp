# Claude Code Integration Configuration

This directory contains comprehensive configuration files for integrating the Kafka Schema Registry MCP Server with Claude Code, providing an AI-native development environment for schema management.

## 📁 Configuration Files

### 1. `claude-code-mcp-config.json`
**Main MCP server configuration for Claude Code**

This file configures the MCP servers and Claude Code-specific settings:
- **MCP Server Setup**: Configures both single and multi-registry MCP servers
- **AI Assistance**: Enables auto-completion, real-time validation, and intelligent suggestions
- **Environment Support**: Local, staging, and production configurations

**Key Features:**
- Schema management capabilities
- Context-aware operations
- Migration and export functionality
- Multi-registry support for disaster recovery

### 2. `claude-code-workspace-config.json`
**Workspace-level configuration for Kafka schema projects**

This file defines the workspace behavior and AI assistance features:
- **Schema Generation**: Templates for events, entities, commands, aggregates
- **Migration Assistance**: Auto-planning and compatibility analysis
- **Documentation Generation**: Multiple format support (Markdown, Avro IDL, JSON Schema)
- **Code Generation**: Producer/consumer code in multiple languages
- **Validation Rules**: Real-time syntax checking and best practices enforcement

**Key Features:**
- Context isolation and switching
- Team collaboration tools
- Automated workflows
- Performance optimizations

### 3. `claude-code-commands-config.json`
**AI-enhanced commands configuration**

This file defines custom commands with AI workflows:
- **Schema Commands**: Analyze, generate, and evolve schemas with AI guidance
- **Migration Commands**: Plan and execute migrations with monitoring
- **Export Commands**: Smart export strategy selection
- **Documentation Commands**: Comprehensive documentation generation

**Key Features:**
- 10 AI-enhanced commands with keyboard shortcuts
- Multi-step workflows with MCP endpoint integration
- Real-time validation and compatibility checking

### 4. `claude-code-templates-config.json`
**Schema templates with AI prompts**

This file provides schema templates for different architectural patterns:
- **Event Schema**: Domain event templates with metadata support
- **Entity Schema**: Business entity templates with lifecycle management
- **Command Schema**: CQRS command templates with audit trails
- **Aggregate Schema**: Domain aggregate templates with state management
- **Value Object Schema**: Immutable value object templates
- **API Response Schema**: Standardized API response templates

**Key Features:**
- 6 comprehensive schema templates
- AI-powered template selection
- Field generation assistance
- Template consistency validation

## 🚀 Quick Setup

### 1. Install Claude Code
Download and install Claude Code from the official website.

### 2. Copy Configuration Files
Copy the configuration files to your Claude Code configuration directory:

```bash
# Create Claude Code config directory (if it doesn't exist)
mkdir -p ~/.claude-code/

# Copy main configuration
cp claude-code-mcp-config.json ~/.claude-code/mcp-config.json

# Copy workspace configuration
cp claude-code-workspace-config.json ~/.claude-code/workspace.json

# Copy commands configuration
cp claude-code-commands-config.json ~/.claude-code/commands.json

# Copy templates configuration
cp claude-code-templates-config.json ~/.claude-code/templates.json
```

### 3. Set Up Project Structure
Create the required directory structure in your workspace:

```bash
# Create Claude Code directories
mkdir -p .claude-code/templates/
mkdir -p .claude-code/commands/

# Copy workspace-specific configs
cp claude-code-workspace-config.json .claude-code/workspace.json
cp claude-code-commands-config.json .claude-code/commands/
cp claude-code-templates-config.json .claude-code/templates/
```

### 4. Configure Environment Variables
Set up environment variables for the MCP server:

```bash
# Basic configuration
export SCHEMA_REGISTRY_URL=http://localhost:8081
export MCP_SERVER_PORT=38000
export DEFAULT_CONTEXT=development

# Optional: Multi-registry setup
export MULTI_REGISTRY_CONFIG=multi_registry.env
export PRIMARY_SCHEMA_REGISTRY_URL=http://localhost:8081
export DR_SCHEMA_REGISTRY_URL=http://localhost:8082
```

### 5. Start MCP Server
Ensure your MCP server is running:

```bash
# Start single registry MCP server
python kafka_schema_registry_unified_mcp.py

# Or start multi-registry MCP server
python remote-mcp-server.py
```

## 🔧 Configuration Customization

### Environment-Specific Setup

#### Local Development
```json
{
    "local": {
        "schema_registry_url": "http://localhost:8081",
        "mcp_server_url": "http://localhost:38000",
        "multi_mcp_server_url": "http://localhost:39000"
    }
}
```

#### Staging Environment
```json
{
    "staging": {
        "schema_registry_url": "http://staging.example.com:8081",
        "mcp_server_url": "http://staging.example.com:38000",
        "multi_mcp_server_url": "http://staging.example.com:39000"
    }
}
```

#### Production Environment
```json
{
    "production": {
        "schema_registry_url": "http://prod.example.com:8081",
        "mcp_server_url": "http://prod.example.com:38000",
        "multi_mcp_server_url": "http://prod.example.com:39000"
    }
}
```

### AI Features Configuration

#### Enable/Disable Features
```json
{
    "ai_assistance": {
        "schema_generation": { "enabled": true },
        "migration_assistance": { "enabled": true },
        "documentation_generation": { "enabled": true },
        "code_generation": { "enabled": false }
    }
}
```

#### Validation Rules
```json
{
    "validation_rules": {
        "avro_syntax": { "enabled": true, "real_time": true },
        "compatibility_checking": { "enabled": true },
        "naming_conventions": { "enabled": true },
        "best_practices": { "enabled": true }
    }
}
```

## ⌨️ Keyboard Shortcuts

The configuration includes these keyboard shortcuts:

| Shortcut | Command | Description |
|----------|---------|-------------|
| `Ctrl+Shift+A` | `schema:analyze` | AI-powered schema analysis |
| `Ctrl+Shift+G` | `schema:generate` | Generate schema from description |
| `Ctrl+Shift+E` | `schema:evolve` | Evolve existing schema |
| `Ctrl+Shift+M` | `migration:plan` | Plan migration between contexts |
| `Ctrl+Shift+X` | `migration:execute` | Execute migration with monitoring |
| `Ctrl+Shift+O` | `export:smart` | Smart export strategy |
| `Ctrl+Shift+V` | `compatibility:check` | Compatibility validation |
| `Ctrl+Shift+D` | `documentation:generate` | Generate documentation |
| `Ctrl+Shift+C` | `context:compare` | Compare contexts |
| `Ctrl+Shift+B` | `backup:create` | Create intelligent backup |

## 🎯 Usage Examples

### Schema Generation
1. Open Claude Code in your schema project
2. Press `Ctrl+Shift+G` or use the command palette
3. Describe your schema requirements in natural language
4. Claude Code will generate the appropriate Avro schema

### Migration Planning
1. Press `Ctrl+Shift+M` to open migration planner
2. Select source and target contexts
3. Claude Code analyzes differences and creates migration plan
4. Review and execute the migration

### Documentation Generation
1. Press `Ctrl+Shift+D` to generate documentation
2. Select format (Markdown, Avro IDL, JSON Schema)
3. Claude Code creates comprehensive documentation
4. Documentation includes examples and relationships

## 🔍 Troubleshooting

### MCP Server Connection Issues
```bash
# Check if MCP server is running
curl http://localhost:38000/health

# Check Schema Registry connection
curl http://localhost:8081/subjects
```

### Configuration Validation
```bash
# Validate JSON configuration files
python -m json.tool claude-code-mcp-config.json
python -m json.tool claude-code-workspace-config.json
```

### Logs and Debugging
- Check Claude Code logs in the developer console
- Enable debug logging in the MCP server
- Verify environment variables are set correctly

## 📚 Related Documentation

- [IDE Integration Guide](../docs/ide-integration.md) - Complete integration guide
- [MCP Tools Reference](../docs/mcp-tools-reference.md) - All available MCP tools
- [Use Cases](../docs/use-cases.md) - Real-world usage examples
- [Deployment Guide](../docs/deployment.md) - Production deployment

## 🤝 Contributing

When contributing to Claude Code integration:

1. Test all configuration files with a clean Claude Code installation
2. Validate JSON syntax and schema compliance
3. Update documentation for new features
4. Provide usage examples for new commands or templates
5. Ensure backward compatibility with existing configurations

## 📝 Version History

- **v1.0**: Initial Claude Code integration support
- **v1.1**: Added multi-registry configuration support
- **v1.2**: Enhanced AI assistance features
- **v1.3**: Added comprehensive template system
- **v1.4**: Improved validation and error handling

---

**Happy Schema Development with Claude Code! 🤖🚀** 