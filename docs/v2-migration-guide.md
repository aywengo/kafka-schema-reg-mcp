# v2.0.0 Migration Guide - FastMCP 2.8.0+ Testing

This guide helps teams migrate from the current stable version (v1.8.3) to test the new v2.0.0 release with **FastMCP 2.8.0+ framework** and **MCP 2025-06-18 specification compliance**.

## 🚨 Important Version Information

- **Current Stable**: v1.8.3 (`:stable` tag)
- **Testing Release**: v2.0.0 (`:2.0.0` tag)
- **Promotion**: `:stable` is manually promoted after production validation

> **⚠️ Warning**: v2.0.0 is for testing only. Do not use in production until it's promoted to `:stable`.

## 🔄 Migration Overview

### What's Changed in v2.0.0
- **FastMCP 2.8.0+ Framework**: Complete migration from legacy `mcp[cli]==1.9.4`
- **MCP 2025-06-18 Compliance**: Full support for latest MCP specification
- **Enhanced Authentication**: Native FastMCP BearerAuth with OAuth 2.0
- **Improved Client API**: Modern FastMCP client interface
- **Better Performance**: Enhanced reliability and error handling

### What Stays the Same
- ✅ **All 48 MCP Tools**: Identical functionality and API
- ✅ **Configuration**: Same environment variables
- ✅ **Claude Desktop**: Same integration patterns
- ✅ **Docker Usage**: Same deployment approach

## 🧪 Testing Migration Steps

### Step 1: Backup Current Configuration
```bash
# Backup your current Claude Desktop config
cp ~/Library/Application\ Support/Claude/claude_desktop_config.json \
   ~/claude_desktop_config_v1.8.3_backup.json

# Or on Linux
cp ~/.config/claude-desktop/config.json \
   ~/.config/claude-desktop/config_v1.8.3_backup.json
```

### Step 2: Install v2.0.0 Configuration
```bash
# Copy v2.0.0 configuration
cp config-examples/claude_desktop_v2_config.json \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Or with OAuth testing
cp config-examples/claude_desktop_v2_oauth_config.json \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### Step 3: Pull v2.0.0 Image
```bash
# Pull the v2.0.0 testing image
docker pull aywengo/kafka-schema-reg-mcp:2.0.0
```

### Step 4: Test Basic Functionality
```bash
# Test the v2.0.0 server
python tests/test_mcp_server.py

# Or quick diagnostic
python tests/diagnose_test_environment.py
```

### Step 5: Test with Claude Desktop
1. Restart Claude Desktop
2. Test basic commands:
   ```
   Human: "List all schema contexts"
   Human: "Show me registry information"
   Human: "Test the FastMCP connection"
   ```

## 🔐 OAuth Authentication Testing

### Azure AD Setup (v2.0.0)
```bash
# Configure OAuth environment
export ENABLE_AUTH=true
export AUTH_PROVIDER=azure
export AUTH_ISSUER_URL=https://login.microsoftonline.com/YOUR_TENANT/v2.0
export AZURE_CLIENT_ID=your_client_id
export AZURE_CLIENT_SECRET=your_client_secret
```

### Development Token Testing
```bash
# Test with development tokens
export OAUTH_TOKEN="dev-token-read,write,admin"  # Full access
export OAUTH_TOKEN="dev-token-read"              # Read-only
```

## 🔄 Rolling Back

If you encounter issues with v2.0.0, easily roll back:

### Rollback Steps
```bash
# 1. Restore v1.8.3 configuration
cp ~/claude_desktop_config_v1.8.3_backup.json \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json

# 2. Restart Claude Desktop

# 3. Test functionality
python tests/test_mcp_server.py
```

## 📊 Feature Comparison

| Feature | v1.8.3 (Stable) | v2.0.0 (Testing) |
|---------|-----------------|-------------------|
| **MCP Framework** | Legacy mcp[cli] 1.9.4 | ✅ FastMCP 2.8.0+ |
| **MCP Specification** | Pre-2025 | ✅ MCP 2025-06-18 |
| **Authentication** | Basic | ✅ FastMCP BearerAuth + OAuth |
| **Client API** | Legacy ClientSession | ✅ Modern FastMCP Client |
| **Performance** | Standard | ✅ Enhanced |
| **Error Handling** | Basic | ✅ Improved |
| **OAuth Providers** | 0 | ✅ 5 (Azure, Google, Keycloak, Okta, GitHub) |
| **Tools Count** | 48 | 48 (same) |
| **Configuration** | Same | Same |
| **Production Ready** | ✅ Yes | ⚠️ Testing Only |

## 🧪 Testing Checklist

### Basic Functionality
- [ ] Server starts without errors
- [ ] Claude Desktop connects successfully
- [ ] Basic MCP tools work (`list_subjects`, `get_schema`)
- [ ] Context operations work (`list_contexts`, `create_context`)
- [ ] Export functions work (`export_schema`, `export_context`)

### Enhanced Features (v2.0.0)
- [ ] FastMCP client connection is faster
- [ ] Error messages are more helpful
- [ ] OAuth authentication works (if configured)
- [ ] OAuth discovery endpoints respond
- [ ] Development tokens work for testing

### Regression Testing
- [ ] All existing Claude Desktop prompts work
- [ ] Multi-registry support unchanged
- [ ] Async operations function correctly
- [ ] Docker deployment works
- [ ] Environment variables work as expected

## 🚀 Feedback and Issues

### Reporting Issues
If you encounter problems with v2.0.0:
1. **Document the issue** with specific error messages
2. **Include configuration** used (redact sensitive data)
3. **Test rollback** to confirm v1.8.3 works
4. **Report via GitHub Issues** with `v2.0.0-testing` label

### Success Reports
If v2.0.0 works well for your use case:
1. **Document your setup** (configuration, use cases)
2. **Report performance improvements** you notice
3. **Share OAuth integration** experience (if applicable)

## 📅 Promotion Timeline

v2.0.0 will be promoted to `:stable` after:
- ✅ **Testing Period**: 2-4 weeks of community testing
- ✅ **Issue Resolution**: All critical issues resolved
- ✅ **Production Validation**: Successful production deployments
- ✅ **Performance Verification**: Confirmed performance improvements
- ✅ **OAuth Validation**: Authentication system proven reliable

---

**Ready to test v2.0.0 with FastMCP 2.8.0+? Start with the basic configuration and gradually test advanced features!** 🚀 