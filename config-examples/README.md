# Configuration Examples

This directory contains example Claude Desktop configuration files for different deployment scenarios of the Kafka Schema Registry MCP Server.

## 📂 Available Configurations

### Single Registry Configurations
- **`claude_desktop_config.json`** - Basic local Python configuration (unified)
- **`claude_desktop_docker_config.json`** - Docker latest tag configuration
- **`claude_desktop_stable_config.json`** - Docker stable tag configuration (recommended)
- **`claude_desktop_readonly_config.json`** - Read-only mode for production safety

### Modular Architecture Configurations (v1.8.1+)
- **`claude_desktop_modular_config.json`** - Local Python modular architecture
- **`claude_desktop_modular_docker_config.json`** - Docker modular architecture configuration

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

## 🚀 Quick Start

### For Production (Recommended)
```bash
# Copy stable configuration
cp config-examples/claude_desktop_stable_config.json ~/.config/claude-desktop/config.json

# Or for macOS
cp config-examples/claude_desktop_stable_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
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

### Use Case: Modular Architecture Development (v1.8.1+)
**Recommended:** `claude_desktop_modular_config.json`
- ✅ New modular architecture
- ✅ Better code organization
- ✅ Improved maintainability
- ✅ Focused module responsibilities

### Use Case: Production Safety
**Recommended:** `claude_desktop_readonly_config.json`
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
   - Update `SCHEMA_REGISTRY_URL_X` with your registry endpoints
   - Set `SCHEMA_REGISTRY_USER_X` and `SCHEMA_REGISTRY_PASSWORD_X` for authentication
   - Configure `READONLY_X` for production safety
3. **Test** the configuration before deploying to Claude Desktop
4. **Save** to your Claude Desktop configuration location
5. **Restart** Claude Desktop

## 🔗 Related Documentation

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