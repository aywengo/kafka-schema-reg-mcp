# Configuration Examples

This directory contains example Claude Desktop configuration files for different deployment scenarios of the Kafka Schema Registry MCP Server v3.0 with **FastMCP 4.1+** and **MCP 2026-07-28**.

## 📂 Available Configurations

### Single Registry Configurations
- **`claude_desktop_config.json`** - Basic local Python configuration (unified)
- **`claude_desktop_docker_config.json`** - Docker latest tag configuration
- **`claude_desktop_stable_config.json`** - Docker stable tag configuration (recommended)
- **`claude_desktop_viewonly_config.json`** - View-only mode for production safety
- **`claude_desktop_viewer_config.json`** - Viewer edition (39 tools, default)
- **`claude_desktop_editor_config.json`** - Editor edition (42 tools)
- **`claude_desktop_admin_config.json`** - Admin edition (66 tools)

### Version-Specific Configurations

#### Current Stable (v3.0.0)
- **`claude_desktop_stable_config.json`** - Current stable release, viewer edition
- **`claude_desktop_docker_config.json`** - Latest Docker image, viewer edition

#### Historical FastMCP 2.x Configurations (v2.0.0)
These files are kept for older deployments; use the 3.0 configurations for new work.
- **`claude_desktop_v2_config.json`** - FastMCP 2.x framework (v2.0.0)
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

## 🎛️ Edition Configuration

`MCP_EDITION` selects the tool surface. The default is `viewer`.

| File | Edition | Tools |
|---|---|---|
| `claude_desktop_viewer_config.json` | viewer | 39 |
| `claude_desktop_editor_config.json` | editor | 42 |
| `claude_desktop_admin_config.json` | admin | 66 |

```bash
cp config-examples/claude_desktop_admin_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

`SLIM_MODE=true` is a deprecated alias for `editor`. Do not set it together
with `MCP_EDITION`; the server refuses to start. See
[../docs/editions.md](../docs/editions.md) for the full tool list.

## 🚀 Quick Start

### For Production (Recommended - Current Stable v3.0.0)
```bash
# Copy stable configuration (v3.0.0)
cp config-examples/claude_desktop_stable_config.json ~/.config/claude-desktop/config.json

# Or for macOS
cp config-examples/claude_desktop_stable_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### For Historical FastMCP 2.8.0 Deployments (v2.0.0)
```bash
# Copy the v2.0.0 configuration for an older deployment
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
cd tests && ./run_all_tests.sh --quick

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

**📖 Complete Testing Guide**: [`TESTING_SETUP_GUIDE.md`](../TESTING_SETUP_GUIDE.md)

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

### Use Case: Current Production (Stable v3.0.0)
**Recommended:** `claude_desktop_stable_config.json` for read-only, or `claude_desktop_admin_config.json` for full access
- ✅ 3.0 stable release
- ✅ `viewer` by default; choose `editor` or `admin` explicitly
- ✅ 39 / 42 / 66 tools by edition
- ✅ Multi-registry, background tasks and MRTR workflows

### Use Case: Historical FastMCP 2.x Deployment (v2.0.0)
**Recommended only for existing v2.0.0 deployments:** `claude_desktop_v2_config.json` or `claude_desktop_v2_oauth_config.json`
- FastMCP 2.8.0 and MCP 2025-06-18
- OAuth 2.1 generic discovery
- Use the [v3.0 migration guide](../docs/v3-migration-guide.md) to upgrade

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

- **[v3.0 Migration Guide](../docs/v3-migration-guide.md)** - Upgrade to FastMCP 4, editions and MRTR
- **[TESTING_SETUP_GUIDE.md](../TESTING_SETUP_GUIDE.md)** - Complete testing and troubleshooting guide
- **[TESTING_SETUP_GUIDE.md](../TESTING_SETUP_GUIDE.md)** - Testing environment setup
- **[tests/README.md](../tests/README.md)** - Testing infrastructure details
- **[tests/README.md](../tests/README.md)** - Test suite layout and runners

## 📊 Port Configurations

All configurations in this directory use the updated port scheme:
- **AKHQ UI**: `http://localhost:38080`
- **DEV Registry**: `http://localhost:38081` (read-write)
- **PROD Registry**: `http://localhost:38082` (read-only)
- **Kafka DEV**: `localhost:39092` (external)
- **Kafka PROD**: `localhost:39093` (external)

## ✅ Configuration Validation

### Before Deploying to Claude Desktop
1. **Environment Check**: `cd tests && ./run_all_tests.sh --quick`
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
1. **Run diagnostic**: `cd tests && ./run_all_tests.sh --quick`
2. **Check Schema Registry**: `curl http://localhost:38081/subjects`
3. **Test MCP server**: `cd tests && python test_mcp_server.py`
4. **Verify paths**: Ensure file paths in configuration are correct
5. **Check permissions**: Ensure Python and Docker have necessary permissions

### Common Issues
- **Missing dependencies**: `pip install -r requirements.txt`
- **Port conflicts**: `lsof -i :38081` and kill conflicting processes
- **Docker not running**: Start Docker Desktop or daemon
- **Permission denied**: `chmod +x tests/*.sh`

**📖 Complete Troubleshooting**: [`TESTING_SETUP_GUIDE.md`](../TESTING_SETUP_GUIDE.md)
