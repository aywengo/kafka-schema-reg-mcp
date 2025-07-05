# User Roles Quick Reference Card

## MCP Scopes Overview

| Scope | Permissions | Can Do |
|-------|-------------|--------|
| **`read`** | View-only | List schemas, get configs, compare registries |
| **`write`** | Read + Modify | Register schemas, update configs (includes `read`) |
| **`admin`** | Full access | Delete subjects, migrate schemas (includes `write` + `read`) |

## Azure AD / Entra ID

### ⚡ Quick Setup
```bash
# 1. Create App Roles in Azure Portal
# App Registrations → Your App → App roles → Create:
# - Role Value: "read", "write", "admin"

# 2. Assign Users to Roles  
# Enterprise Applications → Your App → Users and groups → Add user

# 3. Configure Token Claims
# App registrations → Token configuration → Add "roles" claim
```

### 👤 Assign Role to User
1. **Azure Portal** → **Enterprise Applications** → **Your MCP App**
2. **Users and groups** → **Add user/group**
3. Select user and assign role: `read`, `write`, or `admin`

### 🔍 JWT Token Result
```json
{
  "roles": ["read", "write"],
  "sub": "user@company.com"
}
```

---

## Google OAuth 2.0

### ⚡ Quick Setup
```bash
# 1. Create Groups in Google Admin
gam create group mcp-readers@company.com
gam create group mcp-writers@company.com  
gam create group mcp-admins@company.com

# 2. Add users to groups
gam update group mcp-readers@company.com add member user@company.com
```

### 👤 Assign Role to User
1. **Google Admin Console** → **Directory** → **Groups**
2. Select group: `mcp-readers@company.com`, `mcp-writers@company.com`, or `mcp-admins@company.com`
3. **Add members** → Enter user email

### 🔍 JWT Token Result  
```json
{
  "groups": ["mcp-readers@company.com", "mcp-writers@company.com"],
  "email": "user@company.com"
}
```

---

## Keycloak

### ⚡ Quick Setup
```bash
# 1. Create Realm Roles
# Keycloak Admin → Realm Settings → Roles → Add Role:
# - "mcp-reader", "mcp-writer", "mcp-admin"

# 2. Configure role mappers to include in JWT
# Client Scopes → roles → Mappers → realm roles
```

### 👤 Assign Role to User
1. **Keycloak Admin Console** → **Users** → **Select User**
2. **Role Mappings** tab
3. **Assign role**: `mcp-reader`, `mcp-writer`, or `mcp-admin`

### 🔍 JWT Token Result
```json
{
  "realm_access": {
    "roles": ["mcp-reader", "mcp-writer"]
  },
  "preferred_username": "user"
}
```

---

## Okta

### ⚡ Quick Setup
```bash
# 1. Create Custom User Attribute
# Okta Admin → Directory → Profile Editor → User → Add Attribute:
# - Name: "mcp_scopes", Type: string array

# 2. Configure Authorization Server Claim
# Security → API → Authorization Servers → Add Claim:
# - Name: "scope", Value: Arrays.flatten(user.mcp_scopes)
```

### 👤 Assign Role to User
1. **Okta Admin Console** → **Directory** → **People** → **Select User**
2. **Profile** tab → **Edit**
3. Set **mcp_scopes** to: `["read"]`, `["read", "write"]`, or `["read", "write", "admin"]`

### 🔍 JWT Token Result
```json
{
  "mcp_scopes": ["read", "write"],
  "email": "user@company.com"
}
```

---

## Testing Role Assignment

### 🧪 Test Development Tokens
```bash
# Test with curl
curl -H "Authorization: Bearer dev-token-read" http://localhost:8000/list_subjects
curl -H "Authorization: Bearer dev-token-read,write" http://localhost:8000/register_schema  
curl -H "Authorization: Bearer dev-token-read,write,admin" http://localhost:8000/delete_subject
```

### 🔍 Decode Real JWT Tokens
```bash
# Decode JWT to verify scopes
echo "YOUR_JWT_TOKEN" | cut -d. -f2 | base64 -d | jq .
```

### ✅ Verify MCP Integration
```python
# Run test script
python examples/test-user-roles.py
```

---

## Production Deployment

### 🚀 Deploy with Helm
```bash
# Azure AD
cp helm/examples/values-azure.yaml helm/values-production.yaml
helm upgrade --install mcp-server . -f values-production.yaml

# Google OAuth  
cp helm/examples/values-google.yaml helm/values-production.yaml
helm upgrade --install mcp-server . -f values-production.yaml

# Keycloak
cp helm/examples/values-keycloak.yaml helm/values-production.yaml
helm upgrade --install mcp-server . -f values-production.yaml

# Okta
cp helm/examples/values-okta.yaml helm/values-production.yaml  
helm upgrade --install mcp-server . -f values-production.yaml
```

### 🔧 Environment Variables
```bash
export ENABLE_AUTH=true
export AUTH_ISSUER_URL="https://your-provider.com"
export AUTH_VALID_SCOPES="read,write,admin"
export AUTH_REQUIRED_SCOPES="read"
```

---

## Common Role Patterns

### 📊 Typical Role Distribution
- **Developers**: `read` scope (view schemas, compare registries)
- **DevOps Engineers**: `read,write` scope (register schemas, update configs)  
- **Platform Admins**: `read,write,admin` scope (full access including deletions)
- **Auditors**: `read` scope (view-only access for compliance)

### 🏢 Team-Based Assignment
```
Development Team → read scope
QA Team → read scope  
Release Engineering → read,write scope
Platform Team → read,write,admin scope
Security Team → read scope (audit access)
```

### 🔄 Role Progression
```
Junior Developer → read scope
Senior Developer → read,write scope  
Tech Lead → read,write,admin scope
```

---

## Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| ❌ No scopes in JWT | Check claim mapping in OAuth provider |
| ❌ Access denied | Verify user has required role assigned |
| ❌ Wrong scope format | Check JWT claim name (`scope` vs `roles` vs `groups`) |
| ❌ Group not working | Ensure group claim is configured in token |
| ❌ Role not inherited | Check scope hierarchy (admin → write → read) |

### 🔍 Debug Commands
```bash
# Check OAuth configuration
docker exec mcp-server python -c "from oauth_provider import get_oauth_scopes_info; print(get_oauth_scopes_info())"

# Validate JWT token format
curl -H "Authorization: Bearer YOUR_TOKEN" http://mcp-server/health
```

---

## Security Checklist

- [ ] ✅ Users have minimum required scope (principle of least privilege)
- [ ] ✅ Admin scope limited to platform administrators only
- [ ] ✅ Production registries use VIEWONLY mode for most users
- [ ] ✅ JWT tokens have short expiration (1-4 hours)
- [ ] ✅ Role assignments are group-based, not individual
- [ ] ✅ Regular audit of user role assignments (quarterly)
- [ ] ✅ Scope validation is enforced in application logic
- [ ] ✅ OAuth provider is configured with proper security policies

💡 **Pro Tip**: Start with `read` scope for all users, then gradually grant `write` and `admin` based on job requirements. 