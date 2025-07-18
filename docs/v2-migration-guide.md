# v2.x Migration Guide - Current Stable Versions

This guide helps teams migrate from v1.x versions to the current stable v2.x release series with **FastMCP 2.8.0+ framework** and **MCP 2025-06-18 specification compliance**.

## 🚀 Current Version Information

- **Latest Stable**: v2.0.2 (`:stable` tag)
- **Previous Stable**: v1.8.3 (deprecated)
- **Upgrade Path**: v1.x → v2.0.2 (direct upgrade supported)

> **✅ Production Ready**: v2.0.x series is stable and production-ready. Use `:stable` tag for automatic updates to latest stable version.

## 🔄 Migration Overview

### What's New in v2.0.2 (Latest)
- **🔒 Security Enhancements**: Complete credential protection in logging and object representations
- **🤖 Interactive Schema Migration**: Smart migration with user preference elicitation
- **💾 Automatic Backups**: Pre-migration backup creation with error handling
- **✅ Post-Migration Verification**: Comprehensive schema validation and comparison
- **🛡️ Enhanced Error Handling**: Robust handling of migration scenarios

### What's New in v2.0.1
- **📈 Performance Improvements**: Major code refactoring with 2,442 lines of redundant code removed
- **🛡️ Enhanced Schema Validation**: Local JSON schema handling with zero network dependencies
- **🎭 Advanced Elicitation**: Improved user interaction and confirmation workflows

### What's New in v2.0.0
- **🚀 FastMCP 2.8.0+ Framework**: Complete migration from legacy `mcp[cli]==1.9.4`
- **📊 MCP 2025-06-18 Compliance**: Full support for latest MCP specification
- **🔐 OAuth 2.1 Generic Discovery**: 75% less configuration - works with any OAuth 2.1 provider
- **🔗 Resource Linking**: HATEOAS navigation in tool responses

### What Stays the Same
- ✅ **All 48+ MCP Tools**: Identical functionality and API
- ✅ **Configuration**: Same environment variables and setup
- ✅ **Claude Desktop**: Same integration patterns
- ✅ **Docker Usage**: Same deployment approach

## 🚀 Migration Steps

### Step 1: Backup Current Configuration
```bash
# Backup your current Claude Desktop config
cp ~/Library/Application\ Support/Claude/claude_desktop_config.json \
   ~/claude_desktop_config_v1_backup.json

# Or on Linux
cp ~/.config/claude-desktop/config.json \
   ~/.config/claude-desktop/config_v1_backup.json
```

### Step 2: Update to Latest Stable
```bash
# Pull the latest stable version
docker pull aywengo/kafka-schema-reg-mcp:stable

# Verify you have v2.0.2 or later
docker run --rm aywengo/kafka-schema-reg-mcp:stable python -c "import os; print('Version check passed')"
```

### Step 3: Update Claude Desktop Configuration
```bash
# Use the latest stable configuration
cp config-examples/claude_desktop_stable_config.json \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Or for multi-registry setup
cp config-examples/claude_desktop_multi_registry_docker.json \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### Step 4: Test Migration
```bash
# Test the upgraded server
cd tests/
./run_all_tests.sh --quick

# Or comprehensive testing
./run_all_tests.sh
```

### Step 5: Verify with Claude Desktop
1. Restart Claude Desktop
2. Test basic commands:
   ```
   Human: "List all schema contexts"
   Human: "Show me registry information and version"
   Human: "Test the interactive migration features"
   ```

## 🔐 OAuth 2.1 Universal Configuration

### Simplified Setup (v2.0.x)
```bash
# Universal OAuth 2.1 - Works with ANY provider!
export ENABLE_AUTH=true
export AUTH_ISSUER_URL="https://your-oauth-provider.com"
export AUTH_AUDIENCE="your-client-id-or-api-identifier"
```

### Provider Examples

**Azure AD:**
```bash
export AUTH_ISSUER_URL="https://login.microsoftonline.com/your-tenant-id/v2.0"
export AUTH_AUDIENCE="your-azure-client-id"
```

**Google OAuth 2.0:**
```bash
export AUTH_ISSUER_URL="https://accounts.google.com"
export AUTH_AUDIENCE="your-client-id.apps.googleusercontent.com"
```

**Okta:**
```bash
export AUTH_ISSUER_URL="https://your-domain.okta.com/oauth2/default"
export AUTH_AUDIENCE="your-okta-client-id"
```

**Any OAuth 2.1 Provider:**
```bash
export AUTH_ISSUER_URL="https://your-oauth-provider.com"
export AUTH_AUDIENCE="your-client-id"
```

### Migration from v1.x Provider-Specific Configuration
```bash
# OLD (v1.x) - Deprecated
export AUTH_PROVIDER=azure
export AZURE_TENANT_ID=your-tenant
export AZURE_CLIENT_ID=your-client-id
export AZURE_CLIENT_SECRET=your-client-secret

# NEW (v2.x) - Recommended universal approach
export AUTH_ISSUER_URL="https://login.microsoftonline.com/your-tenant/v2.0"
export AUTH_AUDIENCE="your-client-id"
```

### Development Token Testing
```bash
# Test with development tokens (unchanged)
export OAUTH_TOKEN="dev-token-read,write,admin"  # Full access
export OAUTH_TOKEN="dev-token-read"              # Read-only
```

### Testing OAuth 2.1 Discovery
```bash
# Test discovery endpoints
curl http://localhost:8000/.well-known/oauth-authorization-server | jq
curl http://localhost:8000/.well-known/oauth-protected-resource | jq

# MCP tool testing
"Test the OAuth discovery endpoints and show me what providers are supported"
```

## 🤖 Interactive Migration Features (v2.0.2+)

### Smart Schema Migration
The v2.0.2 release introduces intelligent schema migration with user preference elicitation:

```bash
# In Claude Desktop, use natural language:
"Migrate the user-events schema from development to production"

# The system will intelligently ask:
# - Should I replace the existing schema?
# - Should I create a backup first?
# - Should I preserve schema IDs?
# - Should I verify the migration afterward?
```

### Migration Features
- **🔍 Pre-Migration Intelligence**: Automatically detects target schema existence
- **💾 Conditional Backup**: Creates backups only when needed and requested
- **✅ Post-Migration Verification**: Validates schema content, IDs, and compatibility
- **🛡️ Safety Checks**: Prevents accidental overwrites through user confirmation
- **📊 Comprehensive Reporting**: Detailed results with audit trails

## 🔄 Rolling Back

If you encounter issues with v2.x, you can easily roll back:

### Rollback Steps
```bash
# 1. Pull previous stable version (not recommended for long-term)
docker pull aywengo/kafka-schema-reg-mcp:1.8.3

# 2. Restore v1.x configuration
cp ~/claude_desktop_config_v1_backup.json \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json

# 3. Restart Claude Desktop and test
```

## 📊 Version Comparison

| Feature | v1.8.3 (Legacy) | v2.0.2 (Current) |
|---------|------------------|------------------|
| **MCP Framework** | Legacy mcp[cli] 1.9.4 | ✅ FastMCP 2.8.0+ |
| **MCP Specification** | Pre-2025 | ✅ MCP 2025-06-18 |
| **Authentication** | Provider-specific OAuth | ✅ Universal OAuth 2.1 Discovery |
| **Configuration Complexity** | 8+ variables per provider | ✅ 2 variables (universal) |
| **OAuth Standards** | Custom implementations | ✅ RFC 8414 + RFC 8692 + RFC 8707 |
| **Provider Support** | 5 hardcoded providers | ✅ Any OAuth 2.1 compliant provider |
| **Interactive Migration** | Manual migration only | ✅ Smart migration with elicitation |
| **Security Features** | Basic | ✅ Enhanced with credential protection |
| **Performance** | Standard | ✅ Optimized with code refactoring |
| **Resource Linking** | None | ✅ HATEOAS navigation |
| **Schema Validation** | Network-dependent | ✅ Local with zero dependencies |
| **Error Handling** | Basic | ✅ Comprehensive with recovery |
| **Production Ready** | ⚠️ Legacy | ✅ Current Stable |

## 🧪 Validation Checklist

### Basic Functionality
- [ ] Server starts without errors using `:stable` tag
- [ ] Claude Desktop connects successfully
- [ ] Basic MCP tools work (`list_subjects`, `get_schema`)
- [ ] Context operations work (`list_contexts`, `create_context`)
- [ ] Export functions work (`export_schema`, `export_context`)

### Enhanced Features (v2.0.x)
- [ ] FastMCP client connection is faster and more reliable
- [ ] Error messages are clearer and more helpful
- [ ] OAuth authentication works with simplified configuration
- [ ] OAuth discovery endpoints respond correctly
- [ ] Development tokens work for testing
- [ ] Interactive migration prompts work correctly

### Performance & Security (v2.0.2)
- [ ] No credential exposure in logs
- [ ] Migration backups work automatically
- [ ] Post-migration verification passes
- [ ] Performance improvements are noticeable
- [ ] Schema validation works without network calls

### Regression Testing
- [ ] All existing Claude Desktop prompts work
- [ ] Multi-registry support unchanged
- [ ] Async operations function correctly
- [ ] Docker deployment works with `:stable` tag
- [ ] Environment variables work as expected

## 🎯 Best Practices for v2.x

### Docker Tag Strategy
- **Production**: Use `:stable` tag for automatic stable updates
- **Testing**: Use specific version tags like `:2.0.2` for testing
- **Development**: Use `:latest` for cutting-edge features (may be unstable)

### Configuration Management
- **Environment Variables**: Use the new simplified OAuth 2.1 configuration
- **Secrets**: Store sensitive values in proper secret management systems
- **Versioning**: Keep configuration versions aligned with deployment versions

### Monitoring & Observability
- **Health Checks**: Use the enhanced health endpoints
- **Logging**: Benefit from improved logging with credential protection
- **Metrics**: Monitor interactive migration success rates and performance

## 🚀 Feedback and Support

### Getting Help
- **Documentation**: Check [docs/](.) for comprehensive guides
- **Issues**: Report problems via [GitHub Issues](https://github.com/aywengo/kafka-schema-reg-mcp/issues)
- **Testing**: Use the test suite in [tests/](../tests/) for validation

### Success Stories
If v2.x works well for your use case:
1. **Share your setup** via GitHub discussions
2. **Document performance improvements** you notice
3. **Report OAuth integration** success with different providers

---

**Ready to upgrade to v2.0.2? The stable release brings significant improvements in performance, security, and user experience!** 🚀🔒✨

## 📦 Tools to Resources Migration

### **Breaking Change: Tools Migrated to Resources**

Several tools have been migrated to MCP resources for better performance and caching:

| **Old Tool** | **New Resource** | **Migration Required** |
|-------------|------------------|----------------------|
| `list_subjects` | `registry://{name}/subjects` | ✅ **YES** |
| `list_registries` | `registry://names` | ✅ **YES** |
| `list_contexts` | `registry://{name}/contexts` | ✅ **YES** |
| `get_schema` | `schema://{name}/{context}/{subject}` | ✅ **YES** |
| `get_schema_versions` | `schema://{name}/{context}/{subject}/versions` | ✅ **YES** |
| `get_global_config` | `registry://{name}/config` | ✅ **YES** |
| `get_subject_config` | `subject://{name}/{context}/{subject}/config` | ✅ **YES** |
| `get_mode` | `registry://mode` | ✅ **YES** |
| `get_subject_mode` | `subject://{name}/{context}/{subject}/mode` | ✅ **YES** |

### **Migration Examples**

#### **List Subjects Migration**
```python
# ❌ OLD WAY (No longer works)
result = await client.call_tool("list_subjects", {"context": "production"})

# ✅ NEW WAY (Use resources)
result = await client.read_resource("registry://default/subjects")
# or for specific registry:
result = await client.read_resource("registry://production/subjects")
```

#### **List Registries Migration**
```python
# ❌ OLD WAY (No longer works)
result = await client.call_tool("list_registries", {})

# ✅ NEW WAY (Use resources)
result = await client.read_resource("registry://names")
```

#### **Get Schema Migration**
```python
# ❌ OLD WAY (No longer works)
result = await client.call_tool("get_schema", {
    "subject": "user-events",
    "context": "production"
})

# ✅ NEW WAY (Use resources)
result = await client.read_resource("schema://default/production/user-events")
# or for specific registry:
result = await client.read_resource("schema://prod-registry/production/user-events")
```

### **Response Format Changes**

Resources return data in a different format than tools:

```python
# Tool response (old)
if result.content and len(result.content) > 0:
    data = json.loads(result.content[0].text)

# Resource response (new)
if result.contents and len(result.contents) > 0:
    data = json.loads(result.contents[0].text)
```

### **Benefits of Resources**

- 🚀 **Better Performance**: Resources can be cached by MCP clients
- 📊 **Structured Data**: More predictable data format
- 🔄 **Real-time Updates**: Resources can be updated without tool calls
- 💰 **Lower Token Usage**: Reduced overhead for LLM interactions

### **Migration Checklist**

- [ ] Update all `call_tool("list_subjects", ...)` to `read_resource("registry://.../subjects")`
- [ ] Update all `call_tool("list_registries", ...)` to `read_resource("registry://names")`
- [ ] Update all `call_tool("get_schema", ...)` to `read_resource("schema://...")`
- [ ] Change response parsing from `result.content` to `result.contents`
- [ ] Update error handling for resource-specific errors
- [ ] Test all resource URIs with your registry configuration

### **Resource URI Patterns**

| **Pattern** | **Description** | **Example** |
|------------|----------------|-------------|
| `registry://names` | List all registries | `registry://names` |
| `registry://info` | Global registry info | `registry://info` |
| `registry://status` | All registry status | `registry://status` |
| `registry://mode` | Global mode info | `registry://mode` |
| `registry://{name}/subjects` | Registry subjects | `registry://prod/subjects` |
| `registry://{name}/contexts` | Registry contexts | `registry://prod/contexts` |
| `registry://{name}/config` | Registry config | `registry://prod/config` |
| `schema://{name}/{context}/{subject}` | Schema content | `schema://prod/users/user-events` |
| `subject://{name}/{context}/{subject}/config` | Subject config | `subject://prod/users/user-events/config` |

### **Resource Discovery Tools**

The MCP server now provides helpful tools to guide clients toward using resources:

#### **1. `list_available_resources()`**
Discover all available resources and their purposes:

```python
# Get comprehensive list of all resources
result = await client.call_tool("list_available_resources", {})
```

**Claude Desktop Usage:**
```
Human: "What resources are available for getting schema information?"

Claude: I'll show you all available resources for schema operations.

[Uses list_available_resources MCP tool]
📋 Available Resources:
   Registry Resources (7):
   • registry://names - List all registries (replaces list_registries)
   • registry://info - Get registry info
   • registry://{name}/subjects - List subjects (replaces list_subjects)
   
   Schema Resources (3):
   • schema://{name}/{context}/{subject} - Get schema content
   • schema://{name}/{context}/{subject}/versions - Get versions
   
   Subject Resources (2):
   • subject://{name}/{context}/{subject}/config - Get config
   • subject://{name}/{context}/{subject}/mode - Get mode
```

#### **2. `suggest_resource_for_tool(tool_name)`**
Get specific migration suggestions for removed tools:

```python
# Get migration suggestion for a specific tool
result = await client.call_tool("suggest_resource_for_tool", {"tool_name": "list_subjects"})
```

**Claude Desktop Usage:**
```
Human: "How do I replace the list_subjects tool with a resource?"

Claude: I'll show you how to migrate from the list_subjects tool to resources.

[Uses suggest_resource_for_tool MCP tool]
🔄 Migration Suggestion for 'list_subjects':
   Status: Migrated to resource
   Use Resource: registry://{name}/subjects
   Example: registry://production/subjects
   
   Migration Code:
   # OLD (removed)
   result = await client.call_tool("list_subjects", {"context": "production"})
   
   # NEW (use resource)
   result = await client.read_resource("registry://production/subjects")
   data = json.loads(result.contents[0].text)
   
   Benefits:
   • Better performance through caching
   • Reduced token usage
   • Real-time data updates
```

#### **3. `generate_resource_templates()`**
Generate resource URI templates for your specific configuration:

```python
# Generate templates for your environment
result = await client.call_tool("generate_resource_templates", {
    "registry_name": "production",
    "context": "users", 
    "subject": "user-events"
})
```

**Claude Desktop Usage:**
```
Human: "Generate resource templates for my production environment"

Claude: I'll generate resource URI templates for your production setup.

[Uses generate_resource_templates MCP tool]
🎯 Resource Templates for Production:
   Registry Resources:
   • List subjects: registry://production/subjects
   • Get config: registry://production/config
   • List contexts: registry://production/contexts
   
   Schema Resources:
   • Get schema: schema://production/users/user-events
   • Get versions: schema://production/users/user-events/versions
   
   Subject Resources:
   • Get config: subject://production/users/user-events/config
   • Get mode: subject://production/users/user-events/mode
   
   Usage Example:
   result = await client.read_resource("registry://production/subjects")
   data = json.loads(result.contents[0].text)
   subjects = data.get("subjects", [])
```

### **Resource URI Patterns**
