# Remote MCP Server Deployment Guide

This guide covers deploying the Kafka Schema Registry MCP Server as a **remote MCP server** compatible with [Anthropic's remote MCP ecosystem](https://docs.anthropic.com/en/docs/agents-and-tools/remote-mcp-servers).

## 🌐 What is a Remote MCP Server?

Remote MCP servers are third-party services that expand LLM capabilities by providing remote access to tools and resources through the MCP protocol. Unlike local MCP servers, remote servers:

- Run as persistent web services with HTTPS endpoints
- Support multiple concurrent clients
- Provide enterprise authentication (OAuth, JWT)
- Can be discovered and used by various MCP clients
- Are accessible from anywhere on the internet

## ✅ Readiness Status

Our Kafka Schema Registry MCP Server is **production-ready** for remote deployment:

- ✅ **FastMCP 2.8.0+ Framework**: Modern MCP architecture with MCP 2025-06-18 specification compliance
- ✅ **Enhanced Authentication**: Native FastMCP BearerAuth provider with OAuth 2.0 support
- ✅ **Multi-Transport Support**: stdio, SSE, and Streamable HTTP transports via FastMCP
- ✅ **Enterprise OAuth**: Azure AD, Google, Keycloak, Okta, GitHub with JWT validation
- ✅ **Production Infrastructure**: Docker, Kubernetes, TLS/HTTPS
- ✅ **48 MCP Tools**: Complete schema registry operations
- ✅ **Multi-Registry Support**: Enterprise-grade functionality
- ✅ **Security**: Role-based access control with scope validation

## 🚀 Quick Remote Deployment

### Option 1: Docker (Development/Testing)

```bash
# Basic remote deployment
docker run -d \
  --name kafka-schema-registry-remote-mcp \
  -p 8000:8000 \
  -e MCP_TRANSPORT=streamable-http \
  -e MCP_HOST=0.0.0.0 \
  -e ENABLE_AUTH=true \
  -e AUTH_PROVIDER=azure \
  -e AZURE_TENANT_ID=your-tenant-id \
  -e AUTH_AUDIENCE=your-client-id \
  aywengo/kafka-schema-reg-mcp:stable \
  python remote-mcp-server.py

# Server accessible at: http://localhost:8000/mcp
```

### Option 2: Kubernetes (Production)

```bash
# Deploy with Helm
helm upgrade --install kafka-schema-registry-remote-mcp . \
  -f helm/values-remote-mcp.yaml \
  --set ingress.hosts[0].host=mcp-schema-registry.your-domain.com \
  --set env.AZURE_TENANT_ID=your-tenant-id \
  --set env.AUTH_AUDIENCE=your-client-id

# Server accessible at: https://mcp-schema-registry.your-domain.com/mcp
```

## 🔐 OAuth Authentication Setup

Remote MCP servers require authentication. Choose your OAuth provider:

### Azure AD Setup

1. **Register Application in Azure Portal**:
   ```bash
   # Create app registration
   az ad app create \
     --display-name "Kafka Schema Registry MCP Server" \
     --sign-in-audience "AzureADMyOrg"
   
   # Note the Application (client) ID and Tenant ID
   ```

2. **Configure Environment Variables**:
   ```bash
   export AZURE_TENANT_ID="your-tenant-id"
   export AZURE_CLIENT_ID="your-client-id"
   export AZURE_CLIENT_SECRET="your-client-secret"
   export AUTH_AUDIENCE="your-client-id"
   
   # SSL/TLS Security Configuration (v2.0.0+)
   export ENFORCE_SSL_TLS_VERIFICATION="true"
   export CUSTOM_CA_BUNDLE_PATH=""  # Optional: path to corporate CA bundle
   ```

3. **Assign User Roles** (see [User Role Assignment Guide](user-role-assignment-guide.md)):
   - Create App Roles: `MCP-Reader`, `MCP-Writer`, `MCP-Admin`
   - Assign users to appropriate roles

### Google OAuth Setup

1. **Create OAuth Application**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create OAuth 2.0 credentials
   - Configure authorized domains

2. **Environment Variables**:
   ```bash
   export AUTH_PROVIDER="google"
   export GOOGLE_CLIENT_ID="your-client-id"
   export GOOGLE_CLIENT_SECRET="your-client-secret"
   export AUTH_AUDIENCE="your-client-id"
   ```

### Keycloak Setup

1. **Create Keycloak Client**:
   ```bash
   export AUTH_PROVIDER="keycloak"
   export KEYCLOAK_SERVER_URL="https://your-keycloak-server"
   export KEYCLOAK_REALM="your-realm"
   export AUTH_ISSUER_URL="https://your-keycloak-server/realms/your-realm"
   ```

### Okta Setup

1. **Create Okta Application**:
   ```bash
   export AUTH_PROVIDER="okta"
   export OKTA_DOMAIN="your-okta-domain"
   export OKTA_CLIENT_ID="your-client-id"
   export OKTA_CLIENT_SECRET="your-client-secret"
   ```

## 🔧 Transport Configuration

### Streamable HTTP (Recommended)

```bash
# Modern HTTP transport
export MCP_TRANSPORT="streamable-http"
export MCP_PATH="/mcp"

# Client connection: https://your-domain.com/mcp
```

### Server-Sent Events (SSE)

```bash
# SSE transport for compatibility
export MCP_TRANSPORT="sse"
export MCP_PATH="/sse"

# Client connection: https://your-domain.com/sse
```

## 🌍 Production Deployment

### Complete Kubernetes Deployment

1. **Prepare Configuration**:
   ```bash
   # Copy and customize values
   cp helm/values-remote-mcp.yaml helm/values-production.yaml
   
   # Edit values-production.yaml:
   # - Set your domain name
   # - Configure OAuth provider
   # - Set Schema Registry connections
   ```

2. **Deploy with TLS**:
   ```bash
   helm upgrade --install kafka-schema-registry-remote-mcp . \
     -f helm/values-production.yaml \
     --namespace mcp-servers \
     --create-namespace
   ```

3. **Verify Deployment**:
   ```bash
   # Check pods
   kubectl get pods -n mcp-servers
   
   # Check ingress
   kubectl get ingress -n mcp-servers
   
   # Test endpoint
   curl https://mcp-schema-registry.your-domain.com/mcp
   ```

### DNS and TLS Configuration

1. **DNS Setup**:
   ```bash
   # Point your domain to the ingress IP
   mcp-schema-registry.your-domain.com → YOUR_INGRESS_IP
   ```

2. **TLS Certificate** (automatic with cert-manager):
   ```yaml
   # In values-production.yaml
   ingress:
     tls:
       - secretName: mcp-schema-registry-tls
         hosts:
           - mcp-schema-registry.your-domain.com
   ```

## 📱 Client Connection Examples

### Claude Desktop Integration

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "kafka-schema-registry-remote": {
      "transport": "http",
      "baseUrl": "https://mcp-schema-registry.your-domain.com/mcp",
      "authentication": {
        "type": "oauth2",
        "oauth2": {
          "authUrl": "https://login.microsoftonline.com/YOUR_TENANT_ID/oauth2/v2.0/authorize",
          "tokenUrl": "https://login.microsoftonline.com/YOUR_TENANT_ID/oauth2/v2.0/token",
          "clientId": "YOUR_CLIENT_ID",
          "scopes": ["openid", "email", "profile"]
        }
      }
    }
  }
}
```

### FastMCP Client (Python) - v2.0.0

```python
from fastmcp import Client
import asyncio

async def main():
    # Connect to remote MCP server using FastMCP 2.8.0+ client
    client = Client("https://mcp-schema-registry.your-domain.com/mcp")
    
    async with client:
        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {len(tools)}")
        
        # Call a tool with enhanced error handling
        result = await client.call_tool("list_subjects", {
            "registry": "production"
        })
        print(f"Subjects: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### curl Testing

```bash
# Test server health
curl -X GET https://mcp-schema-registry.your-domain.com/health

# Test MCP endpoint (requires OAuth token)
curl -X POST https://mcp-schema-registry.your-domain.com/mcp \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

## 🔍 Authentication Testing

### Development Tokens

For testing, use development tokens:

```bash
# Test with read-only access
curl -X POST https://mcp-schema-registry.your-domain.com/mcp \
  -H "Authorization: Bearer dev-token-read" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'

# Test with write access
curl -X POST https://mcp-schema-registry.your-domain.com/mcp \
  -H "Authorization: Bearer dev-token-read,write" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_subjects"}}'
```

### Production JWT Tokens

1. **Obtain Token from OAuth Provider**:
   ```bash
   # Azure AD example
   az account get-access-token \
     --resource YOUR_CLIENT_ID \
     --query accessToken -o tsv
   ```

2. **Use Token in Requests**:
   ```bash
   TOKEN=$(az account get-access-token --resource YOUR_CLIENT_ID --query accessToken -o tsv)
   
   curl -X POST https://mcp-schema-registry.your-domain.com/mcp \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'
   ```

## 📊 Monitoring and Logging

### Health Checks

```bash
# Server health
curl https://mcp-schema-registry.your-domain.com/health

# OAuth configuration
curl https://mcp-schema-registry.your-domain.com/mcp \
  -H "Authorization: Bearer dev-token-read" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "get_oauth_scopes_info"}}'
```

### Kubernetes Monitoring

```bash
# Check logs
kubectl logs -n mcp-servers deployment/kafka-schema-registry-remote-mcp

# Check metrics (if Prometheus enabled)
kubectl port-forward -n mcp-servers svc/kafka-schema-registry-remote-mcp 8000:80
curl http://localhost:8000/metrics
```

## 🛡️ Security Best Practices

### Production Security Checklist

- ✅ **OAuth Authentication**: Always enable OAuth in production
- ✅ **HTTPS/TLS**: Use cert-manager for automatic certificate management
- ✅ **Network Policies**: Restrict ingress/egress traffic
- ✅ **RBAC**: Use Kubernetes RBAC for pod security
- ✅ **Secrets Management**: Store OAuth credentials in Kubernetes secrets
- ✅ **JWT Validation**: Enable cryptographic token validation
- ✅ **Scope-Based Authorization**: Assign minimal required scopes to users
- ✅ **Regular Updates**: Keep Docker images and dependencies updated

### Environment Separation

```bash
# Development
export ENABLE_AUTH="false"  # Development only!
export ENFORCE_SSL_TLS_VERIFICATION="false"  # Development only - not recommended

# Staging  
export ENABLE_AUTH="true"
export AUTH_PROVIDER="azure"
export READONLY_1="false"  # Allow write operations
export ENFORCE_SSL_TLS_VERIFICATION="true"
export CUSTOM_CA_BUNDLE_PATH=""

# Production
export ENABLE_AUTH="true"
export AUTH_PROVIDER="azure"
export READONLY_1="true"   # Read-only for safety
export ENFORCE_SSL_TLS_VERIFICATION="true"
export CUSTOM_CA_BUNDLE_PATH="/etc/ssl/certs/corporate-ca-bundle.pem"  # Optional
```

## 🚀 Submission to Anthropic

To list your remote MCP server in [Anthropic's directory](https://docs.anthropic.com/en/docs/agents-and-tools/remote-mcp-servers):

### Server Information

- **Company**: Your Organization
- **Description**: Kafka Schema Registry MCP Server with OAuth authentication and 48 tools for schema management
- **Server URL**: `https://mcp-schema-registry.your-domain.com/mcp`
- **Authentication**: OAuth 2.0 (Azure AD, Google, Keycloak, Okta)
- **Documentation**: Link to this deployment guide

### Capabilities

- ✅ **48 MCP Tools**: Complete schema registry operations
- ✅ **Multi-Registry Support**: Manage multiple Schema Registry instances
- ✅ **OAuth Authentication**: Enterprise-grade security
- ✅ **Real-time Operations**: Async task management with progress tracking
- ✅ **Schema Migration**: Cross-registry schema migration tools
- ✅ **Context Management**: Production/staging environment isolation

## 🔧 Troubleshooting

### Common Issues

1. **OAuth Token Validation Fails**:
   ```bash
   # Check JWT libraries are installed
   pip install PyJWT cryptography aiohttp
   
   # Verify OAuth configuration
   kubectl logs -n mcp-servers deployment/kafka-schema-registry-remote-mcp | grep "OAuth"
   ```

2. **HTTPS Certificate Issues**:
   ```bash
   # Check cert-manager
   kubectl get certificates -n mcp-servers
   kubectl describe certificate mcp-schema-registry-tls -n mcp-servers
   ```

3. **Transport Connection Issues**:
   ```bash
   # Test transport endpoint
   curl -v https://mcp-schema-registry.your-domain.com/mcp
   
   # Check ingress configuration
   kubectl get ingress -n mcp-servers -o yaml
   ```

### Support and Documentation

- **Remote MCP Guide**: [This document](remote-mcp-deployment.md)
- **OAuth Providers Guide**: [OAuth setup documentation](oauth-providers-guide.md)
- **User Role Assignment**: [Role management guide](user-role-assignment-guide.md)
- **API Reference**: [Complete tool documentation](mcp-tools-reference.md)
- **GitHub Issues**: [Report problems or request features](https://github.com/your-org/kafka-schema-reg-mcp/issues)

---

## Summary

Your Kafka Schema Registry MCP Server is **production-ready** for remote deployment with:

- ✅ **Enterprise Authentication**: OAuth 2.0 with 4 major providers
- ✅ **Modern Transports**: SSE and Streamable HTTP support via FastMCP
- ✅ **Production Infrastructure**: Kubernetes, Helm, TLS, monitoring
- ✅ **Complete Functionality**: 48 tools, multi-registry, async operations
- ✅ **Security**: JWT validation, scope-based authorization, network policies

Deploy with confidence using the configurations in this guide! 