# 🚀 OAuth 2.1 Generic Discovery Guide

**Major Update**: The Kafka Schema Registry MCP Server now uses **generic OAuth 2.1 discovery** instead of provider-specific configurations. This means dramatically simplified setup that works with **any OAuth 2.1 compliant provider**.

## 🎯 The New Approach: Universal OAuth 2.1 Compatibility

### **Before (Provider-Specific - v1.x)**
```bash
# Required 8+ variables per provider
export AUTH_PROVIDER=azure
export AZURE_TENANT_ID=your-tenant
export AZURE_CLIENT_ID=your-client-id
export AZURE_CLIENT_SECRET=your-secret
export AZURE_AUTHORITY=https://login.microsoftonline.com/your-tenant
# ... many more provider-specific variables
```

### **After (Generic OAuth 2.1 - v2.x)**
```bash
# Just 2 core variables for ANY provider!
export AUTH_ISSUER_URL="https://login.microsoftonline.com/your-tenant-id/v2.0"
export AUTH_AUDIENCE="your-azure-client-id"
```

## ✅ Supported OAuth 2.1 Providers

The server now works with **any OAuth 2.1 compliant provider** that supports RFC 8414 discovery:

- **🟦 Azure AD / Entra ID** - Fully OAuth 2.1 compliant
- **🟨 Google OAuth 2.0** - OAuth 2.1 compatible with discovery
- **🟥 Keycloak** - Full OAuth 2.1 support with discovery
- **🟧 Okta** - OAuth 2.1 compliant with enhanced security
- **⚫ GitHub OAuth** - Limited support (fallback configuration)
- **🟪 Custom OAuth 2.1 Providers** - Any RFC 8414 compliant provider

## 🚀 Quick Setup (Any Provider)

### Step 1: Basic OAuth 2.1 Configuration

```bash
# Enable OAuth 2.1 authentication
export ENABLE_AUTH=true

# Set your OAuth provider's issuer URL
export AUTH_ISSUER_URL="https://your-oauth-provider.com"

# Set your client ID or API identifier
export AUTH_AUDIENCE="your-client-id-or-api-identifier"

# Optional: Configure scopes (defaults shown)
export AUTH_VALID_SCOPES="read,write,admin"
export AUTH_DEFAULT_SCOPES="read"
export AUTH_REQUIRED_SCOPES="read"
```

### Step 2: Provider-Specific Issuer URLs

#### 🟦 Azure AD / Entra ID
```bash
export AUTH_ISSUER_URL="https://login.microsoftonline.com/your-tenant-id/v2.0"
export AUTH_AUDIENCE="your-azure-client-id"
```

#### 🟨 Google OAuth 2.0
```bash
export AUTH_ISSUER_URL="https://accounts.google.com"
export AUTH_AUDIENCE="your-client-id.apps.googleusercontent.com"
```

#### 🟥 Keycloak
```bash
export AUTH_ISSUER_URL="https://your-keycloak-server.com/realms/your-realm"
export AUTH_AUDIENCE="your-keycloak-client-id"
```

#### 🟧 Okta
```bash
export AUTH_ISSUER_URL="https://your-domain.okta.com/oauth2/default"
export AUTH_AUDIENCE="api://your-api-identifier"
```

#### ⚫ GitHub (Limited OAuth 2.1 Support)
```bash
export AUTH_ISSUER_URL="https://github.com"
export AUTH_AUDIENCE="your-github-client-id"
```

### Step 3: Test the Configuration

```bash
# Start the MCP server
python kafka_schema_registry_unified_mcp.py

# Test OAuth discovery (should return endpoint metadata)
curl http://localhost:8000/.well-known/oauth-authorization-server | jq

# Test with Claude Desktop
"Test the OAuth discovery endpoints and show me the configuration"
```

## 🔍 How OAuth 2.1 Discovery Works

### **Automatic Endpoint Discovery**

1. **Discovery Request**: Server requests `{AUTH_ISSUER_URL}/.well-known/oauth-authorization-server`
2. **Endpoint Extraction**: Automatically extracts authorization, token, JWKS, and other endpoints
3. **Caching**: Caches discovery metadata with configurable TTL
4. **Fallback**: For non-compliant providers (like GitHub), uses fallback configuration

### **Example Discovery Flow**

```bash
# 1. Server discovers endpoints
GET https://accounts.google.com/.well-known/oauth-authorization-server

# 2. Response includes all necessary endpoints
{
  "issuer": "https://accounts.google.com",
  "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
  "token_endpoint": "https://oauth2.googleapis.com/token",
  "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
  "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
  "revocation_endpoint": "https://oauth2.googleapis.com/revoke"
}

# 3. Server uses discovered endpoints automatically
```

## 🛡️ OAuth 2.1 Security Features

### **Enhanced Security (Automatic)**
- **PKCE Enforcement**: Mandatory Proof Key for Code Exchange with S256
- **Resource Indicators**: RFC 8707 compliance for resource validation
- **Audience Validation**: Ensures tokens are intended for your service
- **JWKS Caching**: Intelligent caching with TTL and refresh

### **Security Configuration**
```bash
# PKCE is mandatory (default)
export REQUIRE_PKCE=true

# Resource validation
export RESOURCE_INDICATORS="https://your-api.com"

# Token binding (if supported by provider)
export TOKEN_BINDING_ENABLED=true

# Audience validation (recommended)
export STRICT_AUDIENCE_VALIDATION=true
```

## 📖 Provider-Specific Setup Guides

### 🟦 Azure AD / Entra ID

#### App Registration Setup
1. Go to **Azure Portal** → **Azure Active Directory** → **App registrations**
2. Click **New registration**
3. Configure:
   - **Name**: `Kafka Schema Registry MCP Server`
   - **Redirect URI**: `https://your-mcp-server.com/auth/callback`
4. Note the **Application (client) ID** and **Directory (tenant) ID**

#### MCP Configuration
```bash
export ENABLE_AUTH=true
export AUTH_ISSUER_URL="https://login.microsoftonline.com/YOUR_TENANT_ID/v2.0"
export AUTH_AUDIENCE="YOUR_AZURE_CLIENT_ID"
```

### 🟨 Google OAuth 2.0

#### Google Cloud Console Setup
1. Create project in **Google Cloud Console**
2. Enable **Google+ API** and **OAuth2 API**
3. Configure **OAuth consent screen**
4. Create **OAuth 2.0 Client ID** credentials
5. Note the **Client ID**

#### MCP Configuration
```bash
export ENABLE_AUTH=true
export AUTH_ISSUER_URL="https://accounts.google.com"
export AUTH_AUDIENCE="YOUR_CLIENT_ID.apps.googleusercontent.com"
```

### 🟥 Keycloak

#### Keycloak Client Setup
1. Login to **Keycloak Admin Console**
2. Create new client: `mcp-schema-registry`
3. Enable **Client authentication** and **Authorization**
4. Set redirect URI: `https://your-mcp-server.com/auth/callback`

#### MCP Configuration
```bash
export ENABLE_AUTH=true
export AUTH_ISSUER_URL="https://your-keycloak-server.com/realms/your-realm"
export AUTH_AUDIENCE="mcp-schema-registry"
```

### 🟧 Okta

#### Okta App Integration Setup
1. Login to **Okta Admin Console**
2. Create **Web Application** integration
3. Configure redirect URIs and scopes
4. Note the **Client ID** and **Domain**

#### MCP Configuration
```bash
export ENABLE_AUTH=true
export AUTH_ISSUER_URL="https://your-domain.okta.com/oauth2/default"
export AUTH_AUDIENCE="YOUR_OKTA_CLIENT_ID"
```

### ⚫ GitHub (Special Handling)

GitHub has limited OAuth 2.1 support, so the server uses fallback configuration:

#### GitHub OAuth App Setup
1. Go to **Settings** → **Developer settings** → **OAuth Apps**
2. Create **New OAuth App**
3. Configure callback URL: `https://your-mcp-server.com/auth/callback`

#### MCP Configuration
```bash
export ENABLE_AUTH=true
export AUTH_ISSUER_URL="https://github.com"
export AUTH_AUDIENCE="YOUR_GITHUB_CLIENT_ID"

# GitHub-specific fallback (automatically detected)
# Server will use GitHub's API endpoints when discovery fails
```

## 🔧 Migration from v1.x Provider-Specific Setup

### **Automatic Migration**

The server automatically detects and migrates legacy configurations:

```bash
# OLD (v1.x) - Still works but deprecated
export AUTH_PROVIDER=azure
export AZURE_TENANT_ID=your-tenant
export AZURE_CLIENT_ID=your-client

# NEW (v2.x) - Recommended
export AUTH_ISSUER_URL="https://login.microsoftonline.com/your-tenant/v2.0"
export AUTH_AUDIENCE="your-client"
```

### **Migration Steps**

1. **Update Environment Variables**:
   ```bash
   # Remove old provider-specific variables
   unset AUTH_PROVIDER AZURE_TENANT_ID AZURE_CLIENT_ID AZURE_CLIENT_SECRET
   unset GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET
   unset OKTA_DOMAIN OKTA_CLIENT_ID OKTA_CLIENT_SECRET
   
   # Add new generic variables
   export AUTH_ISSUER_URL="https://your-oauth-provider.com"
   export AUTH_AUDIENCE="your-client-id"
   ```

2. **Update Helm Values**:
   ```yaml
   # OLD values.yaml
   auth:
     provider: azure
     azure:
       tenantId: "your-tenant"
       clientId: "your-client"
   
   # NEW values.yaml
   auth:
     oauth2:
       issuerUrl: "https://login.microsoftonline.com/your-tenant/v2.0"
       audience: "your-client"
   ```

3. **Test Migration**:
   ```bash
   # Verify discovery works
   curl http://localhost:8000/.well-known/oauth-authorization-server
   
   # Test with MCP client
   "Test the OAuth discovery endpoints"
   ```

## 🎯 Benefits of Generic OAuth 2.1 Approach

### **🚀 Simplified Configuration**
- **75% fewer environment variables** (2 vs 8+ per provider)
- **No provider-specific knowledge** required
- **Universal configuration** works with any OAuth 2.1 provider

### **🔮 Future-Proof Architecture**
- **New providers work automatically** without code changes
- **Standards-based approach** using RFC 8414 discovery
- **Automatic endpoint updates** when providers change URLs

### **🛡️ Enhanced Security**
- **OAuth 2.1 compliance** with PKCE, Resource Indicators
- **Automatic security feature detection** from discovery metadata
- **Better token validation** with proper audience checking

### **🔧 Easier Maintenance**
- **No provider-specific bugs** to fix
- **Reduced complexity** in codebase (~75% less provider code)
- **Self-healing configuration** via discovery refresh

## 🧪 Testing OAuth 2.1 Integration

### **Discovery Endpoint Testing**
```bash
# Test discovery endpoints
curl http://localhost:8000/.well-known/oauth-authorization-server | jq
curl http://localhost:8000/.well-known/oauth-protected-resource | jq

# MCP tool testing
"Test the OAuth discovery endpoints and show me what providers are supported"
```

### **Token Validation Testing**
```bash
# Development tokens (for testing only)
export OAUTH_TOKEN="dev-token-read,write,admin"

# Test with real OAuth provider
# (Follow your provider's OAuth flow to get real tokens)
```

### **End-to-End Testing**
```bash
# Run the comprehensive OAuth test suite
cd tests/
python test_oauth_discovery.py
python test_oauth.py
python test_github_oauth.py
```

## 🤝 Contributing

If your OAuth 2.1 provider isn't working correctly:

1. **Check Discovery Support**: Does your provider support RFC 8414?
   ```bash
   curl https://your-provider.com/.well-known/oauth-authorization-server
   ```

2. **Report Issues**: Create an issue with:
   - Provider name and discovery URL
   - Discovery response (if any)
   - Error messages from the MCP server

3. **Add Fallback Support**: For non-compliant providers, we can add fallback configurations like we did for GitHub.

## 📚 Additional Resources

- **[OAuth 2.1 Specification](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1)** - Official OAuth 2.1 spec
- **[RFC 8414](https://tools.ietf.org/html/rfc8414)** - OAuth 2.0 Authorization Server Metadata
- **[RFC 8692](https://tools.ietf.org/html/rfc8692)** - OAuth 2.0 Protected Resource Metadata
- **[RFC 8707](https://tools.ietf.org/html/rfc8707)** - Resource Indicators for OAuth 2.0
- **[Main README](../README.md)** - Complete MCP server documentation
- **[API Reference](api-reference.md)** - Detailed API documentation

---

> **🎉 The OAuth 2.1 generic discovery approach represents a major architectural improvement**, reducing complexity while increasing compatibility and future-proofing the authentication system. The days of provider-specific configuration are over! 🚀 