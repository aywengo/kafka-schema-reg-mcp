# Documentation Index

Welcome to the Kafka Schema Registry MCP Server v3.0 documentation! This folder covers the **FastMCP 4.1+ / MCP SDK 2** stack with **MCP 2026-07-28** compliance, the three runtime editions, **Enhanced Authentication**, **MRTR workflows**, and **Advanced Security Features**.

## 🤖 **MCP Implementation Overview**

This project uses **FastMCP 4.1+** on **MCP Python SDK 2** for **MCP 2026-07-28** compliance, while still serving `2025-11-25` clients from the same process. It integrates with Claude Desktop and other MCP clients. Users interact with schema management through natural language commands.

### **Key MCP Features:**
- ✅ **FastMCP 4.1+ / MCP SDK 2**: Dual-era protocol negotiation in one process
- ✅ **MCP 2026-07-28 Compliance**: Modern sessionless protocol with `2025-11-25` fallback
- ✅ **Three editions**: `viewer` (39 tools), `editor` (42) and `admin` (66) from one codebase
- ✅ **Enhanced Authentication**: OAuth 2.1 discovery with scope-based tool permissions
- ✅ **MRTR workflows**: Guided schema evolution, migration, context reorganization and disaster recovery
- ✅ **Advanced Security**: Credential protection, secure logging and VIEWONLY enforcement at the HTTP boundary
- ✅ **Subject Aliasing**: `add_subject_alias` and `delete_subject_alias` tools
- ✅ **Claude Desktop Ready**: Direct AI integration for schema management
- ✅ **Natural Language Interface**: No curl commands or API knowledge required
- ✅ **Context-Aware Operations**: All tools support schema contexts
- ✅ **Export Capabilities**: JSON and Avro IDL formats with comprehensive metadata
- ✅ **Background Tasks**: Non-blocking operations with progress tracking
- ✅ **Multi-Registry Support**: Manage up to 8 Schema Registry instances

---

## 📚 Available Documentation

### 🎯 **[Use Cases](use-cases.md)** - AI-Assisted Schema Management
Real-world scenarios using Claude Desktop integration:
- **Enterprise Use Cases**: Multi-environment management with AI assistance
- **Development Workflows**: AI-guided schema evolution and compatibility testing
- **Export & Documentation**: Human-readable schema documentation generation
- **Compliance & Governance**: AI-assisted regulatory compliance checking
- **Configuration Management**: Natural language configuration commands
- **MRTR Workflows**: Guided schema evolution, migration, context reorganization and disaster recovery
- **Complete Development Lifecycle**: End-to-end workflows with Claude Desktop
- **Async Operations**: Long-running migrations with progress monitoring

### 🚀 **[Deployment Guide](deployment.md)** - Production-Ready Deployments
Comprehensive deployment instructions covering:
- **Docker Deployment**: MCP server containerization and Claude Desktop configuration
- **Kubernetes**: Complete K8s manifests for MCP server deployment
- **Cloud Platforms**: AWS EKS, Google Cloud Run, Azure Container Instances
- **Security**: Authentication, network policies, MCP-specific considerations
- **Monitoring**: MCP server metrics and health monitoring
- **Claude Desktop Configuration**: Best practices and troubleshooting

### 🔧 **[MCP Tools Reference](mcp-tools-reference.md)** - Complete Tool Documentation
Generated reference for the full edition-dependent MCP surface:
- **Edition summary**: `viewer` (39 tools), `editor` (42) and `admin` (66)
- **Tool inventory**: scope, read-only/destructive annotations and parameters for every tool
- **Resources**: 4 concrete resources and 17 resource templates
- **Prompts**: 10 built-in prompts
- **Natural Language Examples**: Claude Desktop usage patterns

The catalog is defined in `tool_catalog.py`; the tables in [editions.md](editions.md) are generated from the same source.

### 🔐 **[OAuth Providers Guide](oauth-providers-guide.md)** - Universal Authentication
OAuth 2.1 generic discovery setup guide:
- **Universal Configuration**: Works with any OAuth 2.1 compliant provider
- **Provider Examples**: Azure AD, Google, Keycloak, Okta, GitHub
- **Migration Guide**: From provider-specific to generic configuration
- **Security Features**: PKCE enforcement, Resource Indicators, Audience validation
- **Discovery Endpoints**: RFC 8414 compliance and automatic endpoint detection

### 📖 **[API Reference](api-reference.md)** - REST API and Tool Inventory
*Note: This document is maintained for reference but the **MCP Tools Reference** is the primary documentation for the current implementation.*

### 🔧 **[IDE Integration](ide-integration.md)** - Development Environment Setup
Development environment setup guides (updated for MCP):
- **Claude Desktop Integration**: Primary interface for schema management
- **Claude Code Integration**: AI-native development environment with advanced MCP capabilities
- **VS Code Integration**: Extensions and workspace configuration for MCP development
- **Cursor Integration**: AI-powered development with MCP server testing

### 🎛️ **[Editions](editions.md)** - Per-edition tool tables and selection

### 🧭 **[Elicitation and MRTR Workflows](elicitation-guide.md)** - Interactive tools on both protocol eras

### 🚚 **[v3.0 Migration Guide](v3-migration-guide.md)** - Upgrade from 2.x

### 🏷️ **[Release Process](release-process.md)** - Candidates, tags and stable promotion

### 📋 **[v2 Migration Guide](v2-migration-guide.md)** - Historical v1 → v2 Guide
Migration guide for the v1 → v2 upgrade. For the current release, use the [v3.0 migration guide](v3-migration-guide.md):
- **v1.x to v2.x Migration**: FastMCP framework upgrade
- **OAuth Migration**: From provider-specific to generic OAuth 2.1
- **Breaking Changes**: JSON-RPC batching removal and other changes
- **Testing Guide**: Validation steps for new versions

### 🗺️ **[v3.0 Design and Roadmap](v3-roadmap.md)** - Implementation Notes
Design, milestones and implementation record for v3.0:
- **MCP 2026-07-28**: FastMCP 4 / MCP SDK 2 upgrade with legacy client support
- **Editions**: `viewer` (read-only), `editor` (read, compatibility, evolution, registration) and `admin` (full access)
- **Roadmap**: Milestones M0-M4, risk register, backward compatibility matrix

---

## 🎉 What's New in v3.0.0 (Latest)

### **🎛️ Editions**
- `viewer` (39 tools), `editor` (42) and `admin` (66) from one codebase
- `SLIM_MODE` is a deprecated alias for `editor`

### **🚀 FastMCP 4 / MCP 2026-07-28**
- Dual-era protocol negotiation in one process
- Native background tasks through `fastmcp-tasks`
- MRTR workflows for schema evolution, migration, context reorganization and disaster recovery

### **📚 Release Notes**
- [CHANGELOG](../CHANGELOG.md)
- [v3.0 migration guide](v3-migration-guide.md)

## 🎉 What's New in v2.1.x

### **🧭 Subject Aliasing**
- New tools for managing subject aliases: `add_subject_alias`, `delete_subject_alias`
- `add_subject_alias` is available in the editor and admin editions; `delete_subject_alias` is admin-only.
- Requires write scope in OAuth-enabled environments

### **Fixes and Enhancements**
- Improvements to Schema Evolution Assistant workflow
- Interactive import fixes and robustness

## 🎉 What's New in v2.0.2

### **🔒 Security Enhancements**
- **SSL/TLS Security Enhancement (Issue #24)**: Explicit SSL certificate verification for all HTTP requests
  - **Secure Sessions**: All Schema Registry and OAuth communications use `verify=True`
  - **Custom CA Bundle Support**: Enterprise environments with corporate certificates
  - **Enhanced Error Handling**: Clear SSL-related error messages and comprehensive logging
  - **Environment Configuration**: `ENFORCE_SSL_TLS_VERIFICATION` and `CUSTOM_CA_BUNDLE_PATH` variables
- **Security Issue #26 Resolution**: Complete credential protection in logging and object representations
- **Secure Header Management**: Dynamic credential generation without persistent storage
- **Logging Security Filter**: Automatic masking of sensitive data in all log messages
- **Safe Object Representations**: Secured `__repr__` and `__str__` methods

### **🤖 Interactive Schema Migration**
- **Smart Migration**: Interactive `migrate_schema_interactive()` with intelligent user preference elicitation
- **Schema Existence Detection**: Automatic target schema detection and conflict resolution
- **User Preference Collection**: Dynamic elicitation for migration decisions
- **Automatic Backups**: Pre-migration backup creation with error handling
- **Post-Migration Verification**: Comprehensive schema validation and comparison
- **Enhanced Result Metadata**: Complete operation context and audit trails

### **🛡️ Robust Error Handling**
- **Elicitation Failures**: Graceful handling when user input cannot be collected
- **Replacement Protection**: Clear error messages when users decline schema replacement
- **Network Resilience**: Enhanced handling of registry connectivity issues

### **📊 New MCP Resources (7 Total)**
- **Global Resources**: Real-time server and registry information via URIs
  - `registry://status` - Overall registry connection status and health
  - `registry://info` - Detailed server configuration and capabilities
  - `registry://mode` - Registry mode detection and MCP compliance info
  - `registry://names` - List of all configured registry names with status
- **Registry-Specific Resources**: Individual registry information
  - `registry://status/{name}` - Specific registry connection status
  - `registry://info/{name}` - Detailed registry configuration
  - `registry://mode/{name}` - Registry operational mode and settings
- **Schema Resources**: Direct schema content access
  - `schema://{name}/{context}/{subject}` - Schema content with explicit context
  - `schema://{name}/{subject}` - Schema content with default context

## 🎉 What's New in v2.0.1

### **📈 Performance & Code Quality**
- **Major Code Refactoring**: Streamlined codebase with improved readability
- **Memory Optimization**: Enhanced logging statements and resource management
- **Clean Architecture**: Removed 2,442 lines of redundant code

### **🛡️ Enhanced Schema Validation**
- **Local JSON Schema Handling**: Custom handler for draft-07 JSON Schema meta-schemas
- **Zero Network Dependencies**: Local schema resolution prevents external requests
- **Improved Performance**: Faster validation with consistent local behavior

## 🎉 What's New in v2.0.0 - FastMCP 2.8.0+ Framework

### **🚀 FastMCP 2.8.0+ Framework Migration**
- **✅ Modern MCP Architecture**: Complete migration from legacy `mcp[cli]==1.9.4` to FastMCP 2.8.0+
- **✅ MCP 2025-06-18 Compliance**: Protocol version supported at the time of the v2.0 release
- **✅ Enhanced Authentication**: Native FastMCP BearerAuth provider with OAuth 2.1 integration
- **✅ Improved Client API**: Modern FastMCP client interface replacing legacy `mcp.ClientSession`
- **✅ Better Performance**: Enhanced reliability and performance with modern framework
- **✅ 100% Backward Compatibility**: All existing deployments continue to work unchanged

### **🔐 OAuth 2.1 Generic Discovery**
- **Universal Provider Support**: 75% less configuration - works with any OAuth 2.1 provider
- **RFC 8414 Compliance**: Automatic endpoint discovery using OAuth 2.1 standards
- **Enhanced Security**: PKCE enforcement, Resource Indicators (RFC 8707), Audience validation
- **Future-Proof**: No provider-specific code - automatically works with new providers

### **🔗 Resource Linking & Enhanced Responses**
- **HATEOAS Navigation**: All tool responses include `_links` sections for enhanced discoverability
- **Client Integration**: Standard HATEOAS links for rich UI development
- **Consistent URI Scheme**: Uniform addressing across all Schema Registry resources

## 🎉 Previous Versions

### v1.7.0 - Advanced Async Operations
- **Complete Async Task Management System**: Non-blocking operations with real-time progress tracking
- **Task Lifecycle Management**: Create, monitor, cancel tasks with graceful shutdown
- **Enhanced Long-Running Operations**: Migration, cleanup, and comparison operations

### v1.6.0 - Batch Cleanup & Migration Enhancements
- **Batch Cleanup Tools**: Efficient context cleanup with parallel execution
- **Migration Improvements**: Better error handling and progress reporting

### v1.5.0 - Multi-Registry Support
- **Multi-Registry Mode**: Support for up to 8 Schema Registry instances
- **Cross-Registry Tools**: Compare and migrate between registries

---

## 🗺️ Documentation Navigation

### **Getting Started**
1. Start with the main [README](../README.md) for quick setup
2. Review [Use Cases](use-cases.md) to see AI-assisted schema management patterns
3. Check [Deployment Guide](deployment.md) for your environment

### **For Claude Desktop Users**
1. Follow the main [README](../README.md) for Claude Desktop configuration
2. Use [Use Cases](use-cases.md) for natural language interaction patterns
3. Reference [MCP Tools Reference](mcp-tools-reference.md) for specific tool usage

### **For Developers**
1. Review [MCP Tools Reference](mcp-tools-reference.md) for tool development
2. Check [IDE Integration](ide-integration.md) for development setup
3. Use the test scripts: `tests/test_unified.sh`

### **For DevOps/Production**
1. Review [Deployment Guide](deployment.md) for your target platform
2. Configure authentication using [OAuth Providers Guide](oauth-providers-guide.md)
3. Implement monitoring using provided examples

---

## 🤖 Claude Desktop Usage Examples

### **Basic Schema Operations**
```
Human: "List all schema contexts"
Human: "Register a user schema with id, name, and email fields in development"
Human: "Check if adding an age field to the user schema is backward compatible"
Human: "Export the user schema as Avro IDL for documentation"
```

### **Interactive Migration (v2.0.2+)**
```
Human: "Migrate the user-events schema from development to production with backup"
Human: "I want to replace the existing schema but create a backup first"
Human: "Verify the migration was successful"
```

### **Advanced Workflows**
```
Human: "Create a production context and register our order schema with strict FULL compatibility"
Human: "Export all development schemas, check their compatibility with production, then promote the compatible ones"
Human: "Generate a compliance report by exporting all schemas from the GDPR context with full metadata"
```

### **Schema Evolution (NEW!)**
```
Human: "Show me the schema evolution guide"
Human: "Help me safely evolve my user schema"
Human: "Start schema evolution assistant for order-events"
Human: "I need to remove a field from production schema safely"
```

### **Configuration Management**
```
Human: "Set the production context to FULL compatibility mode for maximum safety"
Human: "Switch to read-only mode during maintenance, then back to normal operations"
Human: "Show me the configuration differences between our development and production contexts"
```

---

## 🔗 Quick Links

### **Configuration Examples**
- **Claude Desktop Stable**: [claude_desktop_stable_config.json](../config-examples/claude_desktop_stable_config.json)
- **Claude Code Integration**: [claude-code-mcp-config.json](../config-examples/claude-code-mcp-config.json)
- **Multi-Registry**: [claude_desktop_multi_registry_docker.json](../config-examples/claude_desktop_multi_registry_docker.json)
- **IDE Configurations**: [VS Code](../config-examples/vscode-mcp-settings.json), [Cursor](../config-examples/cursor-mcp-config.json), [JetBrains](../config-examples/jetbrains-mcp-config.xml)
- **Complete Configuration Guide**: [config-examples/README.md](../config-examples/README.md)

### **User Guides**
- **MCP Prompts Guide**: [prompts-guide.md](prompts-guide.md) - All available prompts including Schema Evolution Assistant
- **Workflows Documentation**: [workflows/README.md](workflows/README.md) - Advanced multi-step workflows
- **Elicitation Guide**: [elicitation-guide.md](elicitation-guide.md) - Interactive tools and user input

### **Development & Testing**
- **Main Server**: [kafka_schema_registry_unified_mcp.py](../kafka_schema_registry_unified_mcp.py)
- **Test Runner**: [run_all_tests.sh](../tests/run_all_tests.sh)
- **Testing Guide**: [TESTING_SETUP_GUIDE.md](../TESTING_SETUP_GUIDE.md)

### **Deployment**
- **Docker Compose**: [docker-compose.yml](../docker-compose.yml)
- **Helm Charts**: [helm/](../helm/)
- **Production Examples**: [Deployment Guide](deployment.md)

---

## 📝 Contributing to Documentation

When contributing to the MCP implementation documentation:

1. **Use Cases**: Add natural language interaction examples with Claude Desktop
2. **MCP Tools Reference**: Include comprehensive tool examples and usage patterns
3. **Deployment**: Provide MCP-specific configuration and troubleshooting
4. **Claude Desktop Integration**: Document best practices for AI-assisted workflows
5. **Version Updates**: Keep version references current (latest: v3.0.0)

---

## 🆘 Getting Help

If you need assistance with the MCP implementation:

1. Check [Use Cases](use-cases.md) for Claude Desktop interaction examples
2. Review [MCP Tools Reference](mcp-tools-reference.md) for tool-specific documentation
3. Consult [Deployment Guide](deployment.md) for configuration and setup
4. Test your setup with the provided test scripts

### **Quick Debug Commands**
```bash
# Test unified MCP server directly
python kafka_schema_registry_unified_mcp.py

# Test with Schema Registry integration
cd tests && python test_basic_server.py

# Run comprehensive tests
cd tests && ./run_all_tests.sh

# Test Docker image with stable tag
docker run --rm -i -e SCHEMA_REGISTRY_URL=http://localhost:8081 --network host aywengo/kafka-schema-reg-mcp:stable

# Monitor async operations
python -c "from kafka_schema_registry_unified_mcp import *; print('MCP Server Ready')"
```

---

**Happy Schema Managing with AI, Interactive Operations, and Enhanced Security! 🤖🚀🔒🎉**
