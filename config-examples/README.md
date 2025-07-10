# Configuration Examples

This directory contains example Claude Desktop configuration files for different deployment scenarios of the Kafka Schema Registry MCP Server v2.0.0 with **FastMCP 2.8.0+ framework** and **MCP 2025-06-18 specification compliance**.

## 📂 Available Configurations

### Single Registry Configurations
- **`claude_desktop_config.json`** - Basic local Python configuration (unified)
- **`claude_desktop_docker_config.json`** - Docker latest tag configuration
- **`claude_desktop_stable_config.json`** - Docker stable tag configuration (recommended)
- **`claude_desktop_viewonly_config.json`** - View-only mode for production safety
- **`claude_desktop_slim_mode_config.json`** - SLIM_MODE enabled for reduced LLM overhead (~15 tools)

### Version-Specific Configurations

#### Current Stable (v1.8.3)
- **`claude_desktop_stable_config.json`** - Current stable release (v1.8.3)
- **`claude_desktop_docker_config.json`** - Latest Docker image (may be pre-release)

#### FastMCP 2.8.0+ Configurations (v2.0.0)
- **`claude_desktop_v2_config.json`** - FastMCP 2.8.0+ framework (v2.0.0)
- **`claude_desktop_v2_oauth_config.json`** - v2.0.0 with OAuth 2.1 generic discovery
- **`claude_desktop_v2_multi_registry.json`** - v2.0.0 multi-registry setup

### Multi-Registry Configurations
- **`claude_desktop_numbered_config.json`** - Local Python multi-registry setup
- **`claude_desktop_multi_registry_docker.json`** - Docker multi-registry with full environment variables
- **`claude_desktop_simple_multi.json`** - Simplified 2-registry setup (dev + prod)
- **`claude_desktop_local_testing.json`** - Local testing with multiple logical registries

### Development Configurations
- **`claude_desktop_env_file.json`** - Docker Compose based configuration
- **`claude_desktop_async_monitoring_config.json`** - Optimized for async task monitoring

### IDE MCP Integration Configurations
- **`mcp-ide-integration.md`** - Comprehensive guide for VS Code, Cursor, and JetBrains integration
- **`vscode-mcp-settings.json`** - VS Code MCP client configuration
- **`vscode-mcp-tasks.json`** - VS Code tasks for MCP server management
- **`cursor-mcp-config.json`** - Cursor MCP configuration with AI prompts
- **`jetbrains-mcp-config.xml`** - JetBrains IDEs MCP plugin configuration
- **`docker-compose.mcp.yml`** - Complete MCP development environment
- **`setup-ide-mcp.sh`** - Automated setup script for all IDE integrations

## 🏪 SLIM_MODE Configuration

**SLIM_MODE** reduces the number of exposed tools from 70+ to ~20 essential tools, significantly improving LLM performance.

### When to Use SLIM_MODE
- 🚀 When experiencing slow LLM responses due to too many tools
- 📦 For production environments focused on read-only operations
- 💰 To reduce token usage and costs
- 🎯 When you only need basic schema management capabilities

### How to Enable SLIM_MODE

#### Option 1: Use the Pre-configured File
```bash
# Use the ready-made SLIM_MODE configuration
cp config-examples/claude_desktop_slim_mode_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

#### Option 2: Add to Existing Configuration
Add `SLIM_MODE` to your existing configuration:
```json
"env": {
  "SCHEMA_REGISTRY_URL": "http://localhost:38081",
  "SLIM_MODE": "true"  // Add this line
}
```

### Tools Available in SLIM_MODE
- **Essential Read-Only**: `get_schema`, `list_subjects`, `list_contexts`, `check_compatibility`
- **Basic Write**: `register_schema`, `create_context`
- **Statistics**: `count_contexts`, `count_schemas`
- **Configuration**: `get_global_config`, `get_mode`

### Tools Hidden in SLIM_MODE
- ❌ Migration tools (`migrate_schema`, `migrate_context`)
- ❌ Batch operations (`clear_context_batch`)
- ❌ Export/import tools
- ❌ Interactive/elicitation tools
- ❌ Workflow and task management
- ❌ Delete operations

## 🚀 Quick Start

### For Production (Recommended - Current Stable v1.8.3)
```bash
# Copy stable configuration (v1.8.3)
cp config-examples/claude_desktop_stable_config.json ~/.config/claude-desktop/config.json

# Or for macOS
cp config-examples/claude_desktop_stable_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### For FastMCP 2.8.0+ Testing (v2.0.0)
```bash
# Copy v2.0.0 configuration for testing FastMCP 2.8.0+ features
cp config-examples/claude_desktop_v2_config.json ~/.config/claude-desktop/config.json

# Or for macOS
cp config-examples/claude_desktop_v2_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### For Multi-Registry Setup
```bash
# Copy multi-registry configuration
cp config-examples/claude_desktop_multi_registry_docker.json ~/.config/claude-desktop/config.json

# Or for macOS
cp config-examples/claude_desktop_multi_registry_docker.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### For Local Development
```bash
# Copy local configuration
cp config-examples/claude_desktop_numbered_config.json ~/.config/claude-desktop/config.json

# Or for macOS
cp config-examples/claude_desktop_numbered_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### For IDE MCP Integration

#### Automated Setup (Recommended)
```bash
# Setup everything with one command
./config-examples/setup-ide-mcp.sh --all

# Or setup specific IDEs
./config-examples/setup-ide-mcp.sh --vscode --environment
./config-examples/setup-ide-mcp.sh --cursor --jetbrains
```

#### Manual Setup
```bash
# VS Code setup
mkdir -p .vscode
cp config-examples/vscode-mcp-settings.json .vscode/settings.json
cp config-examples/vscode-mcp-tasks.json .vscode/tasks.json

# Cursor setup
mkdir -p .cursor
cp config-examples/cursor-mcp-config.json .cursor/mcp-config.json

# JetBrains IDEs setup
mkdir -p .idea
cp config-examples/jetbrains-mcp-config.xml .idea/mcp-config.xml

# Start MCP development environment
docker-compose -f config-examples/docker-compose.mcp.yml up -d
```

## 🧪 Testing Your Configuration

Before using any configuration, test that the MCP server works properly:

### Quick Diagnostic
```bash
# Run comprehensive environment check
python tests/diagnose_test_environment.py

# Test MCP server functionality
cd tests && python test_mcp_server.py
```

### Full Testing Suite
```bash
# Start test environment (choose one option)
cd tests
./start_test_environment.sh              # Single registry
./start_multi_registry_environment.sh    # Multi-registry (recommended)

# Run tests
./run_all_tests.sh --quick              # Essential tests (faster)
./run_all_tests.sh                      # Comprehensive test suite
```

**📖 Complete Testing Guide**: [`tests/TEST_ENVIRONMENT_SUMMARY.md`](../tests/TEST_ENVIRONMENT_SUMMARY.md)

## 🔧 Configuration Selection Guide

### Use Case: Basic Schema Registry Access
**Recommended:** `claude_desktop_stable_config.json`
- ✅ Production-ready Docker image
- ✅ Single Schema Registry
- ✅ Stable and tested

### Use Case: Multi-Environment Schema Management
**Recommended:** `claude_desktop_multi_registry_docker.json`
- ✅ Multiple Schema Registry instances
- ✅ Per-registry read-only controls
- ✅ Cross-registry operations
- ✅ Migration and comparison tools

### Use Case: Local Development
**Recommended:** `claude_desktop_numbered_config.json`
- ✅ Local Python execution
- ✅ Easy debugging
- ✅ Fast iteration

### Use Case: Current Production (Stable v1.8.3)
**Recommended:** `claude_desktop_stable_config.json`
- ✅ Battle-tested stable release
- ✅ Proven in production environments
- ✅ Full MCP functionality with 48 tools
- ✅ Multi-registry and async operations support

### Use Case: FastMCP 2.8.0+ Framework Testing (v2.0.0)
**Recommended:** `claude_desktop_v2_config.json` or `claude_desktop_v2_oauth_config.json`
- ✅ Modern FastMCP 2.8.0+ framework
- ✅ MCP 2025-06-18 specification compliance
- ✅ Enhanced authentication with OAuth 2.0 support
- ✅ Better performance and reliability
- ✅ Improved client API and error handling
- ⚠️ **Pre-release**: Use for testing only until promoted to stable

### Use Case: Production Safety
**Recommended:** `claude_desktop_viewonly_config.json`
- ✅ Read-only mode enforced
- ✅ Prevents accidental modifications
- ✅ Safe production monitoring

### Use Case: Async Operations & Long-Running Tasks
**Recommended:** `claude_desktop_async_monitoring_config.json`
- ✅ Optimized for task monitoring
- ✅ Great for migration operations
- ✅ Progress tracking capabilities
- ✅ Long-running operation management

### Use Case: IDE-Native MCP Integration
**Recommended:** `mcp-ide-integration.md` + specific IDE configs
- ✅ Direct MCP protocol integration in IDEs
- ✅ AI-powered schema development
- ✅ Context-aware code completion
- ✅ Integrated schema validation and compatibility checking
- ✅ Multi-registry support in development environment

## 📝 Customization

1. **Copy** the configuration file that best matches your use case
2. **Edit** the environment variables to match your infrastructure:

### 🔒 SSL/TLS Security Configuration (v2.0.0+)

All configurations now support enhanced SSL/TLS security features:

```bash
# Essential security settings (recommended for production)
ENFORCE_SSL_TLS_VERIFICATION=true    # Enable SSL certificate verification (default: true)
CUSTOM_CA_BUNDLE_PATH=""             # Path to custom CA bundle for enterprise environments

# Example: Enterprise environment with custom CA
ENFORCE_SSL_TLS_VERIFICATION=true
CUSTOM_CA_BUNDLE_PATH=/etc/ssl/certs/corporate-ca-bundle.pem

# Example: Development environment (not recommended for production)
ENFORCE_SSL_TLS_VERIFICATION=false
```

**Security Features:**
- 🔒 **Explicit SSL/TLS Certificate Verification** - All HTTP requests use secure sessions
- 🏢 **Custom CA Bundle Support** - Load corporate/internal CA certificates
- 🛡️ **Enhanced Error Handling** - Clear SSL-related error messages and logging
- 📊 **Security Logging** - Comprehensive SSL configuration and event logging

**📚 Complete SSL/TLS Documentation**: [`docs/SSL_TLS_SECURITY.md`](../docs/SSL_TLS_SECURITY.md)
   - Update `SCHEMA_REGISTRY_URL_X` with your registry endpoints
   - Set `SCHEMA_REGISTRY_USER_X` and `SCHEMA_REGISTRY_PASSWORD_X` for authentication
   - Configure `VIEWONLY_X` for production safety
3. **Test** the configuration before deploying to Claude Desktop
4. **Save** to your Claude Desktop configuration location
5. **Restart** Claude Desktop

## 🔗 Related Documentation

- **[v2.0.0 Migration Guide](../docs/v2-migration-guide.md)** - FastMCP 2.8.0+ testing and migration
- **[TEST_ENVIRONMENT_SUMMARY.md](../tests/TEST_ENVIRONMENT_SUMMARY.md)** - Complete testing and troubleshooting guide
- **[TESTING_SETUP_GUIDE.md](../TESTING_SETUP_GUIDE.md)** - Testing environment setup
- **[tests/README.md](../tests/README.md)** - Testing infrastructure details
- **[tests/diagnose_test_environment.py](../tests/diagnose_test_environment.py)** - Environment diagnostic tool

## 📊 Port Configurations

All configurations in this directory use the updated port scheme:
- **AKHQ UI**: `http://localhost:38080`
- **DEV Registry**: `http://localhost:38081` (read-write)
- **PROD Registry**: `http://localhost:38082` (read-only)
- **Kafka DEV**: `localhost:39092` (external)
- **Kafka PROD**: `localhost:39093` (external)

## ✅ Configuration Validation

### Before Deploying to Claude Desktop
1. **Environment Check**: `python tests/diagnose_test_environment.py`
2. **MCP Server Test**: `cd tests && python test_mcp_server.py`
3. **Configuration Test**: `cd tests && python test_simple_config.py`
4. **Schema Registry Check**: `curl http://localhost:38081/subjects`

### Expected Results
When your configuration is working correctly:
- ✅ MCP server starts without errors
- ✅ 68 tools are available
- ✅ Schema Registry connectivity confirmed
- ✅ Basic operations work (list subjects, get schemas)

## ⚡ Quick Commands

```bash
# List all configuration files
ls -la config-examples/

# Preview a configuration
cat config-examples/claude_desktop_stable_config.json

# Validate JSON syntax
python -m json.tool config-examples/claude_desktop_stable_config.json

# Test a configuration before deployment
export SCHEMA_REGISTRY_URL="http://localhost:38081"
python kafka_schema_registry_mcp.py &
PID=$!
sleep 2
cd tests && python test_mcp_server.py
kill $PID

# Copy with backup
cp ~/.config/claude-desktop/config.json ~/.config/claude-desktop/config.json.backup
cp config-examples/claude_desktop_stable_config.json ~/.config/claude-desktop/config.json
```

## 🚨 Troubleshooting

### Configuration Not Working?
1. **Run diagnostic**: `python tests/diagnose_test_environment.py`
2. **Check Schema Registry**: `curl http://localhost:38081/subjects`
3. **Test MCP server**: `cd tests && python test_mcp_server.py`
4. **Verify paths**: Ensure file paths in configuration are correct
5. **Check permissions**: Ensure Python and Docker have necessary permissions

### Common Issues
- **Missing dependencies**: `pip install -r requirements.txt`
- **Port conflicts**: `lsof -i :38081` and kill conflicting processes
- **Docker not running**: Start Docker Desktop or daemon
- **Permission denied**: `chmod +x tests/*.sh`

**📖 Complete Troubleshooting**: [`tests/TEST_ENVIRONMENT_SUMMARY.md`](../tests/TEST_ENVIRONMENT_SUMMARY.md) 