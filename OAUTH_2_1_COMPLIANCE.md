# OAuth 2.1 Resource Server Compliance Guide

This document outlines the comprehensive OAuth 2.1 compliance implementation for the Kafka Schema Registry MCP Server, addressing GitHub issue #35.

## 🚀 Overview

The MCP server has been upgraded to be fully compliant with:
- **OAuth 2.1** specification (draft-ietf-oauth-v2-1)
- **RFC 8692** - OAuth 2.0 Protected Resource Metadata
- **RFC 8707** - OAuth 2.0 Resource Indicators
- **MCP 2025-06-18** specification requirements

## ✅ Implemented OAuth 2.1 Features

### 1. Protected Resource Metadata (RFC 8692) ✅
- **Endpoint**: `/.well-known/oauth-protected-resource`
- **Features**:
  - Resource server identification
  - Supported scopes and descriptions
  - Bearer token methods
  - Authorization server information
  - Resource indicators support

### 2. Resource Indicators (RFC 8707) ✅
- **Implementation**: Full resource indicator validation
- **Configuration**: `RESOURCE_INDICATORS` environment variable
- **Features**:
  - Prevents token misuse across resources
  - Audience validation for all requests
  - Resource-specific access control

### 3. PKCE Enforcement (Mandatory) ✅
- **Implementation**: Proof Key for Code Exchange validation
- **Configuration**: `REQUIRE_PKCE=true` (default)
- **Features**:
  - S256 code challenge method enforcement
  - Reject requests without PKCE
  - Enhanced authorization security

### 4. Discovery Endpoints ✅
- **Fixed Path**: `/.well-known/oauth-authorization-server` (was oauth-authorization-server-custom)
- **Compliance**: Full RFC 8414 metadata
- **Features**:
  - OAuth 2.1 version indicators
  - PKCE requirements disclosure
  - Supported features enumeration

### 5. Token Security Enhancements ✅
- **Development Tokens**: Removed from production (only allowed in development)
- **Token Revocation**: Implemented revocation checking
- **Token Binding**: Support for TLS-based token binding
- **JWKS Cache**: Proper TTL and size management

## 🔧 Configuration

### Environment Variables

```bash
# OAuth 2.1 Core Configuration
ENABLE_AUTH=true
AUTH_PROVIDER=azure|google|keycloak|okta|github|auto
AUTH_ISSUER_URL=https://your-provider.com
AUTH_AUDIENCE=your-api-identifier

# Resource Indicators (RFC 8707)
RESOURCE_INDICATORS=https://api.example.com,https://api2.example.com
RESOURCE_SERVER_URL=https://your-mcp-server.com

# PKCE Configuration (OAuth 2.1)
REQUIRE_PKCE=true
ALLOWED_CODE_CHALLENGE_METHODS=S256

# Token Security
TOKEN_BINDING_ENABLED=true
TOKEN_INTROSPECTION_ENABLED=true
TOKEN_REVOCATION_CHECK_ENABLED=true

# JWKS Cache Management
JWKS_CACHE_TTL=3600
JWKS_CACHE_MAX_SIZE=10

# Development Environment (SECURITY WARNING)
ENVIRONMENT=production
ALLOW_DEV_TOKENS=false  # NEVER set to true in production!
```

### Provider-Specific Configuration

#### Azure AD / Entra ID
```bash
AUTH_PROVIDER=azure
AUTH_ISSUER_URL=https://login.microsoftonline.com/{tenant-id}/v2.0
AUTH_AUDIENCE={client-id}
AZURE_TENANT_ID={your-tenant-id}
```

#### Google OAuth 2.0
```bash
AUTH_PROVIDER=google
AUTH_ISSUER_URL=https://accounts.google.com
AUTH_AUDIENCE={client-id}.apps.googleusercontent.com
```

#### Keycloak
```bash
AUTH_PROVIDER=keycloak
AUTH_ISSUER_URL=https://keycloak.example.com/realms/{realm}
AUTH_AUDIENCE={client-id}
KEYCLOAK_REALM={your-realm}
```

#### Okta
```bash
AUTH_PROVIDER=okta
AUTH_ISSUER_URL=https://{domain}/oauth2/default
AUTH_AUDIENCE=api://{api-identifier}
OKTA_DOMAIN={your-domain}.okta.com
```

## 🔒 Security Features

### 1. Development Token Security
- **Production**: Development tokens (`dev-token-*`) are completely disabled
- **Development**: Only allowed when `ENVIRONMENT=development` AND `ALLOW_DEV_TOKENS=true`
- **Logging**: Security warnings logged when dev tokens are enabled

### 2. Token Validation Pipeline
1. **Format Validation**: JWT structure and headers
2. **Signature Verification**: Using provider JWKS
3. **Expiration Check**: Token lifetime validation
4. **Issuer Validation**: Trusted issuer verification
5. **Audience Validation**: Resource indicator checking
6. **Scope Validation**: Hierarchical scope checking
7. **Revocation Check**: Token revocation status
8. **PKCE Validation**: Code challenge verification

### 3. Scope Hierarchy
```
admin (level 3)
├── write (level 2)
│   └── read (level 1)
```

- **read**: View schemas, subjects, configurations
- **write**: Register schemas, update configs (includes read)
- **admin**: Delete subjects, manage registries (includes write and read)

## 📊 Monitoring & Metrics

### OAuth 2.1 Metrics
The server exposes comprehensive OAuth 2.1 metrics:

```
# PKCE Validation
mcp_oauth_pkce_validation_attempts_total
mcp_oauth_pkce_validation_failures_total

# Resource Indicators
mcp_oauth_resource_indicator_validations_total
mcp_oauth_resource_indicator_failures_total

# Audience Validation
mcp_oauth_audience_validation_failures_total

# Token Management
mcp_oauth_token_revocation_checks_total
mcp_oauth_jwks_cache_hits_total
mcp_oauth_jwks_cache_misses_total
```

### Health Check Compliance
```bash
curl https://your-server.com/health
```

Response includes OAuth 2.1 compliance status:
```json
{
  "status": "healthy",
  "oauth_2_1_compliant": true,
  "mcp_compliance": {
    "oauth_2_1_features": {
      "pkce_required": true,
      "resource_indicators": true,
      "audience_validation": true,
      "token_binding": true,
      "revocation_checking": true
    }
  }
}
```

## 🧪 Testing

### 1. Discovery Endpoint Testing

#### Authorization Server Metadata
```bash
curl https://your-server.com/.well-known/oauth-authorization-server | jq .
```

Expected features:
- `"oauth_version": "2.1"`
- `"require_pkce": true`
- `"code_challenge_methods_supported": ["S256"]`
- `"response_types_supported": ["code"]` (no implicit flow)

#### Protected Resource Metadata
```bash
curl https://your-server.com/.well-known/oauth-protected-resource | jq .
```

Expected features:
- `"oauth_2_1_compliant": true`
- `"resource_indicators_supported": true`
- `"audience_supported": true`
- `"token_binding_methods_supported": ["tls-server-end-point"]`

### 2. Token Validation Testing

#### Valid Token Test
```bash
curl -H "Authorization: Bearer ${VALID_TOKEN}" \
     -H "MCP-Protocol-Version: 2025-06-18" \
     https://your-server.com/mcp
```

#### Invalid Audience Test
```bash
# Token with wrong audience should fail
curl -H "Authorization: Bearer ${WRONG_AUDIENCE_TOKEN}" \
     -H "MCP-Protocol-Version: 2025-06-18" \
     https://your-server.com/mcp
```

#### Insufficient Scope Test
```bash
# Token with only 'read' scope accessing admin endpoint
curl -H "Authorization: Bearer ${READ_ONLY_TOKEN}" \
     -H "MCP-Protocol-Version: 2025-06-18" \
     -X POST https://your-server.com/mcp \
     -d '{"method":"delete_subject",...}'
```

#### Development Token Security Test
```bash
# Should fail in production
curl -H "Authorization: Bearer dev-token-test" \
     -H "MCP-Protocol-Version: 2025-06-18" \
     https://your-server.com/mcp
```

### 3. Provider-Specific Testing

#### Azure AD Testing
```bash
# Get Azure AD token
TOKEN=$(curl -X POST \
  "https://login.microsoftonline.com/${TENANT_ID}/oauth2/v2.0/token" \
  -d "grant_type=client_credentials" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" \
  -d "scope=${AUDIENCE}/.default" | jq -r .access_token)

# Test with MCP server
curl -H "Authorization: Bearer ${TOKEN}" \
     -H "MCP-Protocol-Version: 2025-06-18" \
     https://your-server.com/mcp
```

#### Google OAuth Testing
```bash
# Get Google token (requires proper OAuth flow)
# Test with MCP server
curl -H "Authorization: Bearer ${GOOGLE_TOKEN}" \
     -H "MCP-Protocol-Version: 2025-06-18" \
     https://your-server.com/mcp
```

#### Keycloak Testing
```bash
# Get Keycloak token
TOKEN=$(curl -X POST \
  "${KEYCLOAK_URL}/protocol/openid-connect/token" \
  -d "grant_type=client_credentials" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" | jq -r .access_token)

# Test with MCP server
curl -H "Authorization: Bearer ${TOKEN}" \
     -H "MCP-Protocol-Version: 2025-06-18" \
     https://your-server.com/mcp
```

## 🔍 Troubleshooting

### Common Issues

#### 1. PKCE Validation Failures
**Error**: `"PKCE validation failed"`
**Solution**: Ensure your OAuth client is configured to use PKCE with S256 method

#### 2. Audience Validation Failures
**Error**: `"Invalid audience"`
**Solution**: Configure `AUTH_AUDIENCE` or `RESOURCE_INDICATORS` to match your token's `aud` claim

#### 3. Resource Indicator Mismatches
**Error**: `"Invalid resource indicator"`
**Solution**: Ensure token's resource claim matches configured `RESOURCE_INDICATORS`

#### 4. Development Token Rejection
**Error**: `"Development tokens not allowed in production"`
**Solution**: Either:
- Use proper OAuth tokens in production
- Set `ENVIRONMENT=development` and `ALLOW_DEV_TOKENS=true` for local development

#### 5. JWKS Retrieval Failures
**Error**: `"Failed to retrieve JWKS"`
**Solution**: Check network connectivity to OAuth provider's JWKS endpoint

### Debug Logging

Enable detailed OAuth logging:
```bash
export LOG_LEVEL=DEBUG
export OAUTH_DEBUG=true
```

### Security Validation Checklist

- [ ] Development tokens disabled in production (`ALLOW_DEV_TOKENS=false`)
- [ ] PKCE enforcement enabled (`REQUIRE_PKCE=true`)
- [ ] Resource indicators configured for your environment
- [ ] Audience validation configured (`AUTH_AUDIENCE`)
- [ ] TLS enabled for production (`TLS_ENABLED=true`)
- [ ] Security headers enabled in responses
- [ ] Token revocation checking enabled
- [ ] JWKS cache properly configured

## 📚 References

- [OAuth 2.1 Draft Specification](https://datatracker.ietf.org/doc/draft-ietf-oauth-v2-1/)
- [RFC 8692 - OAuth 2.0 Protected Resource Metadata](https://datatracker.ietf.org/doc/rfc8692/)
- [RFC 8707 - OAuth 2.0 Resource Indicators](https://datatracker.ietf.org/doc/rfc8707/)
- [MCP 2025-06-18 Authorization Specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)

## 🚨 Security Warnings

1. **Never enable development tokens in production environments**
2. **Always use TLS in production (`TLS_ENABLED=true`)**
3. **Configure proper audience validation for your environment**
4. **Regularly rotate OAuth client secrets**
5. **Monitor token revocation and security metrics**
6. **Keep OAuth provider configurations up to date**

## 📝 Migration Guide

### From Previous Version

1. **Update Environment Variables**:
   ```bash
   # Add new OAuth 2.1 variables
   REQUIRE_PKCE=true
   RESOURCE_INDICATORS=https://your-api.com
   TOKEN_BINDING_ENABLED=true
   ```

2. **Update Discovery Endpoint URLs**:
   - Old: `/.well-known/oauth-authorization-server-custom`
   - New: `/.well-known/oauth-authorization-server`

3. **Update OAuth Client Configuration**:
   - Enable PKCE with S256 method
   - Remove implicit flow configuration
   - Configure resource indicators

4. **Update Monitoring**:
   - Add OAuth 2.1 metrics to dashboards
   - Update health check validations
   - Monitor PKCE and resource indicator metrics

5. **Security Review**:
   - Verify development tokens are disabled
   - Review audience and resource indicator configuration
   - Test token validation pipeline
   - Validate security headers
