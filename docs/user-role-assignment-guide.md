# User Role Assignment Guide

This guide shows how to assign MCP scopes (`read`, `write`, `admin`) to specific users in each supported OAuth provider. The MCP server uses these scopes to control access to schema registry operations.

## MCP Scope Definitions

| Scope | Level | Description | Permissions |
|-------|-------|-------------|-------------|
| `read` | 1 | View-only access | Can view schemas, subjects, configurations, compare registries |
| `write` | 2 | Read + Modify | Can register schemas, update configs (includes all `read` permissions) |
| `admin` | 3 | Full access | Can delete subjects, manage registries, migrate schemas (includes all `write` and `read` permissions) |

## How Scopes Work in JWT Tokens

The MCP server validates JWT tokens using real cryptographic signature verification and extracts scopes from the `scope` or `scp` claim:

```json
{
  "sub": "user@company.com",
  "scope": "read write admin",  // OR
  "scp": ["read", "write", "admin"],
  "iss": "https://your-oauth-provider.com",
  "aud": "api://your-app-id",
  "exp": 1640995200,
  "iat": 1640991600
}
```

### JWT Validation Features

✅ **Cryptographic Signature Verification**: Uses provider's public keys from JWKS endpoints  
✅ **Automatic Provider Detection**: Auto-detects Azure, Google, Keycloak, or Okta from token issuer  
✅ **JWKS Caching**: Caches public keys for performance (default 1 hour TTL)  
✅ **Expiration Validation**: Automatically rejects expired tokens  
✅ **Issuer & Audience Validation**: Verifies token comes from correct provider and audience  
✅ **Production Ready**: Full production JWT validation with proper error handling

## Provider-Specific Role Assignment

### 1. Azure AD / Entra ID

#### Method 1: App Roles (Recommended)

**Step 1: Define App Roles in Azure Portal**

1. Go to **Azure Portal** → **App Registrations** → Your MCP App
2. Navigate to **App roles**
3. Create these roles:

```json
[
  {
    "displayName": "Schema Registry Reader",
    "description": "Can view schemas and configurations",
    "value": "read",
    "allowedMemberTypes": ["User"],
    "id": "reader-role-id"
  },
  {
    "displayName": "Schema Registry Writer", 
    "description": "Can register schemas and update configurations",
    "value": "write",
    "allowedMemberTypes": ["User"],
    "id": "writer-role-id"
  },
  {
    "displayName": "Schema Registry Admin",
    "description": "Full access to manage schemas and registries",
    "value": "admin", 
    "allowedMemberTypes": ["User"],
    "id": "admin-role-id"
  }
]
```

**Step 2: Assign Users to Roles**

1. Go to **Enterprise Applications** → Your MCP App
2. Navigate to **Users and groups**
3. Click **Add user/group**
4. Select users and assign appropriate roles

**Step 3: Configure Token Claims**

1. In **App registrations** → **Token configuration**
2. Add optional claim: `roles`
3. The JWT token will include:

```json
{
  "roles": ["read", "write", "admin"]
}
```

#### Method 2: Azure AD Groups

**Step 1: Create Security Groups**

```bash
# Create groups using Azure CLI
az ad group create --display-name "MCP-Readers" --mail-nickname "mcp-readers"
az ad group create --display-name "MCP-Writers" --mail-nickname "mcp-writers"  
az ad group create --display-name "MCP-Admins" --mail-nickname "mcp-admins"
```

**Step 2: Add Users to Groups**

```bash
# Add users to groups
az ad group member add --group "MCP-Readers" --member-id "user-object-id"
az ad group member add --group "MCP-Writers" --member-id "user-object-id"
az ad group member add --group "MCP-Admins" --member-id "user-object-id"
```

**Step 3: Configure Group Claims**

1. In **App registrations** → **Token configuration**
2. Add group claims with mapping:
   - `MCP-Readers` → `read`
   - `MCP-Writers` → `write`
   - `MCP-Admins` → `admin`

### 2. Google OAuth 2.0

#### Method 1: Google Workspace Admin (Recommended)

**Step 1: Create Custom Attributes in Google Admin**

1. Go to **Google Admin Console** → **Directory** → **Users** → **More** → **Manage custom attributes**
2. Create attribute: `mcp_scopes`

**Step 2: Assign Scopes to Users**

1. Edit each user in **Google Admin Console**
2. Set `mcp_scopes` to: `read`, `read write`, or `read write admin`

**Step 3: Configure OAuth Scopes**

In your OAuth application, request scope: `https://www.googleapis.com/auth/admin.directory.user.readonly`

The user info will include custom attributes.

#### Method 2: Google Groups

**Step 1: Create Groups**

```bash
# Using Google Admin API or console
gam create group mcp-readers@your-domain.com
gam create group mcp-writers@your-domain.com  
gam create group mcp-admins@your-domain.com
```

**Step 2: Add Users to Groups**

```bash
gam update group mcp-readers@your-domain.com add member user@your-domain.com
```

**Step 3: Application Logic**

Your application needs to check group membership and map to scopes:

```python
# In token validation
groups = get_user_groups(user_email)
scopes = []
if "mcp-readers@your-domain.com" in groups:
    scopes.append("read")
if "mcp-writers@your-domain.com" in groups:
    scopes.append("write") 
if "mcp-admins@your-domain.com" in groups:
    scopes.append("admin")
```

### 3. Keycloak

#### Method 1: Client Scopes (Recommended)

**Step 1: Create Client Scopes**

1. Go to **Keycloak Admin Console** → **Client Scopes**
2. Create scopes:
   - Name: `mcp-read`, Protocol: `openid-connect`
   - Name: `mcp-write`, Protocol: `openid-connect`
   - Name: `mcp-admin`, Protocol: `openid-connect`

**Step 2: Configure Scope Mappers**

For each client scope, add **Hardcoded claim** mapper:
- Mapper Type: `Hardcoded claim`
- Token Claim Name: `scope`
- Claim value: `read` (or `write`, `admin`)
- Add to access token: `ON`

**Step 3: Assign Scopes to Users**

1. Go to **Users** → Select user → **Client Roles**
2. Or create **Groups** and assign client scopes to groups
3. Add users to appropriate groups

#### Method 2: Realm Roles

**Step 1: Create Realm Roles**

1. **Realm Settings** → **Roles** → **Add Role**
2. Create roles: `mcp-reader`, `mcp-writer`, `mcp-admin`

**Step 2: Configure Role Mappers**

1. **Client Scopes** → **roles** → **Mappers** → **realm roles**
2. Configure to include roles in JWT

**Step 3: Assign Roles to Users**

1. **Users** → Select user → **Role Mappings**
2. Assign appropriate realm roles

### 4. Okta

#### Method 1: Custom Attributes (Recommended)

**Step 1: Create Custom Attribute**

1. Go to **Okta Admin Console** → **Directory** → **Profile Editor**
2. Select **User (default)**
3. Add attribute: `mcp_scopes` (array of strings)

**Step 2: Assign Scopes to Users**

1. Edit user profile
2. Set `mcp_scopes` to: `["read"]`, `["read", "write"]`, or `["read", "write", "admin"]`

**Step 3: Configure Authorization Server**

1. **Security** → **API** → **Authorization Servers**
2. Add claim to token:
   - Name: `scope`
   - Include in token type: `Access Token`
   - Value type: `Expression`
   - Value: `Arrays.flatten(user.mcp_scopes)`

#### Method 2: Okta Groups

**Step 1: Create Groups**

1. **Directory** → **Groups** → **Add Group**
2. Create: `MCP-Readers`, `MCP-Writers`, `MCP-Admins`

**Step 2: Assign Users to Groups**

1. Select group → **Manage People**
2. Add users to appropriate groups

**Step 3: Configure Group Claims**

1. **Authorization Server** → **Claims**
2. Add claim mapping groups to scopes:

```javascript
// Custom expression in claim
String scopes = "";
if (Groups.contains("MCP-Readers")) scopes += "read ";
if (Groups.contains("MCP-Writers")) scopes += "write ";  
if (Groups.contains("MCP-Admins")) scopes += "admin ";
return scopes.trim();
```

## JWT Validation Setup

### 🔧 Production Configuration

To enable real JWT validation, install the required dependencies and configure your provider:

```bash
# Install JWT validation libraries
pip install PyJWT aiohttp cryptography

# Configure environment for your OAuth provider
export ENABLE_AUTH=true
export AUTH_PROVIDER=azure  # or google, keycloak, okta, auto
export AUTH_AUDIENCE=api://your-app-id
export AZURE_TENANT_ID=your-tenant-id  # for Azure
export AUTH_VALID_SCOPES=read,write,admin
```

### 🧪 Testing JWT Validation

Use the comprehensive testing script to validate your configuration:

```bash
# Test with a real JWT token
python examples/test-jwt-validation.py azure "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..."

# Test with automatic provider detection
python examples/test-jwt-validation.py auto "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE2NzA..."

# View configuration examples
python examples/test-jwt-validation.py
```

### 📜 Get Real JWT Tokens

#### Azure AD
```bash
curl -X POST https://login.microsoftonline.com/TENANT_ID/oauth2/v2.0/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=CLIENT_ID&client_secret=CLIENT_SECRET&scope=api://your-app-id/.default"
```

#### Google OAuth
Use [Google OAuth Playground](https://developers.google.com/oauthplayground) or service account authentication.

#### Keycloak
```bash
curl -X POST https://keycloak.company.com/realms/production/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=CLIENT_ID&client_secret=CLIENT_SECRET"
```

#### Okta
```bash
curl -X POST https://your-domain.okta.com/oauth2/default/v1/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=CLIENT_ID&client_secret=CLIENT_SECRET&scope=api://mcp-schema-registry"
```

## Testing Role Assignments

### 1. Verify JWT Token Content

Use [jwt.io](https://jwt.io) to decode your JWT tokens and verify scopes:

```json
{
  "sub": "user@company.com",
  "scope": "read write",
  "roles": ["read", "write"],
  "groups": ["MCP-Writers"],
  "iss": "https://your-provider.com"
}
```

### 2. Test with Production JWT Tokens

```bash
# Test with real JWT token validation (production mode)
curl -H "Authorization: Bearer YOUR_REAL_JWT_TOKEN" \
     http://localhost:8000/mcp/tools/list_subjects

# Test write operations with proper JWT validation
curl -H "Authorization: Bearer YOUR_WRITE_TOKEN" \
     -X POST http://localhost:8000/mcp/tools/register_schema \
     -d '{"subject": "test", "schema": "{\"type\": \"string\"}"}'

# Test admin operations with full JWT validation
curl -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
     -X DELETE http://localhost:8000/mcp/tools/delete_subject/test
```

### 2a. JWT Signature and Claims Validation

The MCP server performs comprehensive JWT validation automatically:

```bash
# The server validates:
# ✅ Cryptographic signature using provider's public keys (JWKS)
# ✅ Token expiration (exp claim)
# ✅ Issuer verification (iss claim) 
# ✅ Audience validation (aud claim)
# ✅ Token issuance time (iat claim)
# ✅ Scope extraction and hierarchy enforcement
# ✅ JWKS caching for performance
```

### 3. Check Scope Validation

Use the MCP tool to verify your token scopes:

```python
# Call get_oauth_scopes_info tool
result = get_oauth_scopes_info()
print(result)
```

## Production Deployment Examples

### Azure AD with Helm

```yaml
# helm/values-azure-roles.yaml
oauth:
  enabled: true
  provider: "azure"
  issuerUrl: "https://login.microsoftonline.com/TENANT_ID/v2.0"
  scopes: ["openid", "email", "profile"]
  claims:
    scope: "roles"  # Use roles claim for scopes

env:
  ENABLE_AUTH: "true"
  AUTH_ISSUER_URL: "https://login.microsoftonline.com/TENANT_ID/v2.0"
  AUTH_VALID_SCOPES: "read,write,admin"
  AUTH_REQUIRED_SCOPES: "read"
```

### Keycloak with Custom Scopes

```yaml
# helm/values-keycloak-scopes.yaml
oauth:
  enabled: true
  provider: "keycloak"
  issuerUrl: "https://keycloak.company.com/realms/production"
  scopes: ["openid", "email", "profile", "mcp-read", "mcp-write", "mcp-admin"]

env:
  ENABLE_AUTH: "true"
  AUTH_ISSUER_URL: "https://keycloak.company.com/realms/production"
  AUTH_VALID_SCOPES: "read,write,admin"
```

## Troubleshooting

### Common Issues

1. **Scopes not in JWT token**
   - Check token configuration in OAuth provider
   - Verify claim mappings
   - Ensure user has assigned roles/groups

2. **Access denied despite having role**
   - Check scope hierarchy (admin includes write and read)
   - Verify JWT token expiration
   - Check claim names (`scope` vs `scp` vs `roles`)

3. **Group membership not reflecting**
   - Check group claim configuration
   - Verify user is in correct groups
   - Check authorization server claim rules

### Debug Commands

```bash
# Decode JWT token
echo "YOUR_JWT_TOKEN" | cut -d. -f2 | base64 -d | jq

# Test MCP server directly
docker run -it --rm aywengo/kafka-schema-reg-mcp:stable \
  python -c "
from oauth_provider import get_oauth_scopes_info
import json
print(json.dumps(get_oauth_scopes_info(), indent=2))
"
```

### VSCode Integration with Roles

```json
{
  "mcp.servers": {
    "kafka-schema-registry": {
      "transport": "http",
      "baseUrl": "https://mcp.company.com",
      "authentication": {
        "type": "oauth2",
        "oauth2": {
          "authUrl": "https://login.microsoftonline.com/TENANT/oauth2/v2.0/authorize",
          "tokenUrl": "https://login.microsoftonline.com/TENANT/oauth2/v2.0/token",
          "clientId": "YOUR_CLIENT_ID",
          "scopes": ["openid", "email", "profile"],
          "additionalParameters": {
            "resource": "YOUR_APP_ID"
          }
        }
      }
    }
  }
}
```

## Security Best Practices

1. **Principle of Least Privilege**: Start with `read` scope, grant `write`/`admin` only when needed
2. **Regular Audits**: Review user role assignments quarterly
3. **Group-Based Assignment**: Use groups instead of individual role assignments
4. **Token Expiration**: Use short-lived tokens (1-4 hours) with refresh tokens
5. **Scope Validation**: Always validate scopes in application logic
6. **Audit Logging**: Log all scope assignments and changes

## Migration from Development to Production

### Development (No Auth)
```bash
# Simple development setup
docker run aywengo/kafka-schema-reg-mcp:stable
```

### Production (With Roles)
```bash
# Deploy with OAuth and role validation
helm upgrade --install mcp-server ./helm \
  -f values-azure-roles.yaml \
  --set oauth.enabled=true
```

Your users will now be properly authenticated and authorized based on their assigned roles! 