# 🔐 OAuth Providers Integration Guide

This guide provides step-by-step instructions for integrating the Kafka Schema Registry MCP Server with popular OAuth 2.0 providers.

## 📋 Supported Providers

- **🟦 Azure AD / Entra ID** - Microsoft's enterprise identity platform
- **🟨 Google OAuth 2.0** - Google's identity and access management
- **🟥 Keycloak** - Open-source identity and access management
- **🟧 Okta** - Enterprise identity and access management
- **⚫ GitHub OAuth** - GitHub's OAuth 2.0 and GitHub Apps authentication

## 🟦 Azure AD / Entra ID Integration

### Prerequisites
- Azure AD tenant
- Azure CLI or access to Azure Portal
- Administrator permissions to create app registrations

### Step 1: Create Azure AD App Registration

#### Using Azure CLI

```bash
# Login to Azure
az login

# Create app registration
az ad app create \
    --display-name "Kafka Schema Registry MCP Server" \
    --sign-in-audience "AzureADMyOrg" \
    --web-redirect-uris "https://your-mcp-server.com/auth/callback"

# Get the Application (client) ID
APP_ID=$(az ad app list --display-name "Kafka Schema Registry MCP Server" --query "[0].appId" -o tsv)
echo "Application ID: $APP_ID"

# Create client secret
az ad app credential reset --id $APP_ID --append --display-name "MCP Server Secret"
```

#### Using Azure Portal

1. Go to **Azure Active Directory** → **App registrations**
2. Click **New registration**
3. Fill in the details:
   - **Name**: `Kafka Schema Registry MCP Server`
   - **Supported account types**: `Accounts in this organizational directory only`
   - **Redirect URI**: `Web` → `https://your-mcp-server.com/auth/callback`
4. Click **Register**
5. Note the **Application (client) ID** and **Directory (tenant) ID**

### Step 2: Configure API Permissions

1. In your app registration, go to **API permissions**
2. Click **Add a permission** → **Microsoft Graph** → **Delegated permissions**
3. Add these permissions:
   - `openid`
   - `email`
   - `profile`
   - `User.Read`
4. Click **Grant admin consent**

### Step 3: Create Client Secret

1. Go to **Certificates & secrets** → **Client secrets**
2. Click **New client secret**
3. Add description: `MCP Server Secret`
4. Set expiration (recommended: 24 months)
5. Click **Add** and copy the secret value

### Step 4: Configure MCP Server

#### Helm Values Configuration

```yaml
# helm/values-azure.yaml
auth:
  enabled: true
  oauth2:
    issuerUrl: "https://login.microsoftonline.com/YOUR_TENANT_ID/v2.0"
    validScopes: "openid,email,profile,https://graph.microsoft.com/User.Read"
    defaultScopes: "openid,email,profile"
    requiredScopes: "openid,email"
    clientRegistrationEnabled: true
    revocationEnabled: true
  createSecret:
    enabled: true
    clientId: "YOUR_AZURE_CLIENT_ID"
    clientSecret: "YOUR_AZURE_CLIENT_SECRET"
```

#### Environment Variables

```bash
# .env file
ENABLE_AUTH=true
AUTH_ISSUER_URL=https://login.microsoftonline.com/YOUR_TENANT_ID/v2.0
AUTH_VALID_SCOPES=openid,email,profile,https://graph.microsoft.com/User.Read
AUTH_DEFAULT_SCOPES=openid,email,profile
AUTH_REQUIRED_SCOPES=openid,email
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret
AZURE_TENANT_ID=your_tenant_id
```

## 🟨 Google OAuth 2.0 Integration

### Prerequisites
- Google Cloud Project
- Google Cloud Console access
- Project owner or editor permissions

### Step 1: Create Google Cloud Project (if needed)

```bash
# Using gcloud CLI
gcloud projects create mcp-schema-registry --name="MCP Schema Registry"
gcloud config set project mcp-schema-registry
```

### Step 2: Enable APIs

1. Go to **Google Cloud Console** → **APIs & Services** → **Library**
2. Enable these APIs:
   - **Google+ API** (for profile access)
   - **Google OAuth2 API**

### Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** (or **Internal** for G Suite)
3. Fill in the application details:
   - **App name**: `Kafka Schema Registry MCP Server`
   - **User support email**: Your email
   - **Developer contact information**: Your email
4. Add scopes: `openid`, `email`, `profile`
5. Save and continue

### Step 4: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth 2.0 Client IDs**
3. Select **Web application**
4. Configure:
   - **Name**: `MCP Server OAuth Client`
   - **Authorized redirect URIs**: `https://your-mcp-server.com/auth/callback`
5. Click **Create** and save the Client ID and Client Secret

### Step 5: Configure MCP Server

#### Helm Values Configuration

```yaml
# helm/values-google.yaml
auth:
  enabled: true
  oauth2:
    issuerUrl: "https://accounts.google.com"
    validScopes: "openid,email,profile"
    defaultScopes: "openid,email,profile"
    requiredScopes: "openid,email"
    clientRegistrationEnabled: true
    revocationEnabled: true
  createSecret:
    enabled: true
    clientId: "YOUR_GOOGLE_CLIENT_ID"
    clientSecret: "YOUR_GOOGLE_CLIENT_SECRET"
```

#### Environment Variables

```bash
# .env file
ENABLE_AUTH=true
AUTH_ISSUER_URL=https://accounts.google.com
AUTH_VALID_SCOPES=openid,email,profile
AUTH_DEFAULT_SCOPES=openid,email,profile
AUTH_REQUIRED_SCOPES=openid,email
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
```

## 🟥 Keycloak Integration

### Prerequisites
- Keycloak server instance
- Realm administrator access
- Keycloak server URL and realm name

### Step 1: Create Keycloak Client

1. Login to **Keycloak Admin Console**
2. Select your realm (or create a new one)
3. Go to **Clients** → **Create client**
4. Configure the client:
   - **Client type**: `OpenID Connect`
   - **Client ID**: `mcp-schema-registry`
   - **Name**: `Kafka Schema Registry MCP Server`
5. Click **Next**

### Step 2: Configure Client Settings

1. **Capability config**:
   - ✅ Client authentication
   - ✅ Authorization
   - ✅ Standard flow
   - ✅ Direct access grants
2. Click **Next**
3. **Login settings**:
   - **Valid redirect URIs**: `https://your-mcp-server.com/auth/callback`
   - **Web origins**: `https://your-mcp-server.com`
4. Click **Save**

### Step 3: Configure Client Scopes

1. Go to **Client scopes** tab
2. Add these default scopes:
   - `openid`
   - `email`
   - `profile`

### Step 4: Get Client Credentials

1. Go to **Credentials** tab
2. Copy the **Client secret**

### Step 5: Configure MCP Server

#### Helm Values Configuration

```yaml
# helm/values-keycloak.yaml
auth:
  enabled: true
  oauth2:
    issuerUrl: "https://your-keycloak-server.com/realms/your-realm"
    validScopes: "openid,email,profile"
    defaultScopes: "openid,email,profile"
    requiredScopes: "openid,email"
    clientRegistrationEnabled: true
    revocationEnabled: true
  createSecret:
    enabled: true
    clientId: "mcp-schema-registry"
    clientSecret: "YOUR_KEYCLOAK_CLIENT_SECRET"
```

#### Environment Variables

```bash
# .env file
ENABLE_AUTH=true
AUTH_ISSUER_URL=https://your-keycloak-server.com/realms/your-realm
AUTH_VALID_SCOPES=openid,email,profile
AUTH_DEFAULT_SCOPES=openid,email,profile
AUTH_REQUIRED_SCOPES=openid,email
KEYCLOAK_CLIENT_ID=mcp-schema-registry
KEYCLOAK_CLIENT_SECRET=your_client_secret
KEYCLOAK_SERVER_URL=https://your-keycloak-server.com
KEYCLOAK_REALM=your-realm
```

## 🟧 Okta Integration

### Prerequisites
- Okta organization
- Okta admin console access
- Okta domain URL

### Step 1: Create Okta Application

1. Login to **Okta Admin Console**
2. Go to **Applications** → **Applications**
3. Click **Create App Integration**
4. Select:
   - **Sign-in method**: `OIDC - OpenID Connect`
   - **Application type**: `Web Application`
5. Click **Next**

### Step 2: Configure Application Settings

1. **General Settings**:
   - **App integration name**: `Kafka Schema Registry MCP Server`
   - **Logo**: Upload if desired
2. **Sign-in redirect URIs**: `https://your-mcp-server.com/auth/callback`
3. **Sign-out redirect URIs**: `https://your-mcp-server.com/logout`
4. **Controlled access**: Choose appropriate assignment
5. Click **Save**

### Step 3: Configure API Scopes

1. Go to **Security** → **API** → **Authorization Servers**
2. Select **default** (or create custom)
3. Go to **Scopes** tab
4. Ensure these scopes exist:
   - `openid`
   - `email`
   - `profile`

### Step 4: Get Application Credentials

1. In your application, go to **General** tab
2. Copy the **Client ID** and **Client secret**
3. Note your **Okta domain** (e.g., `dev-123456.okta.com`)

### Step 5: Configure MCP Server

#### Helm Values Configuration

```yaml
# helm/values-okta.yaml
auth:
  enabled: true
  oauth2:
    issuerUrl: "https://your-domain.okta.com/oauth2/default"
    validScopes: "openid,email,profile"
    defaultScopes: "openid,email,profile"
    requiredScopes: "openid,email"
    clientRegistrationEnabled: true
    revocationEnabled: true
  createSecret:
    enabled: true
    clientId: "YOUR_OKTA_CLIENT_ID"
    clientSecret: "YOUR_OKTA_CLIENT_SECRET"
```

#### Environment Variables

```bash
# .env file
ENABLE_AUTH=true
AUTH_ISSUER_URL=https://your-domain.okta.com/oauth2/default
AUTH_VALID_SCOPES=openid,email,profile
AUTH_DEFAULT_SCOPES=openid,email,profile
AUTH_REQUIRED_SCOPES=openid,email
OKTA_CLIENT_ID=your_client_id
OKTA_CLIENT_SECRET=your_client_secret
OKTA_DOMAIN=your-domain.okta.com
```

## ⚫ GitHub OAuth Integration

### Prerequisites
- GitHub account or GitHub organization
- Repository or organization admin permissions
- GitHub OAuth App or GitHub App

### Step 1: Create GitHub OAuth Application

#### Using GitHub Web Interface

1. Go to **GitHub** → **Settings** → **Developer settings** → **OAuth Apps**
2. Click **New OAuth App**
3. Fill in the application details:
   - **Application name**: `Kafka Schema Registry MCP Server`
   - **Homepage URL**: `https://your-mcp-server.com`
   - **Authorization callback URL**: `https://your-mcp-server.com/auth/callback`
4. Click **Register application**
5. Note the **Client ID** and generate a **Client Secret**

#### Using GitHub CLI

```bash
# Install GitHub CLI if not already installed
# brew install gh  # macOS
# sudo apt install gh  # Ubuntu

# Login to GitHub
gh auth login

# Create OAuth app (requires manual creation via web interface)
echo "Visit https://github.com/settings/applications/new to create OAuth app"
```

### Step 2: Configure Application Settings

1. In your OAuth app settings, configure:
   - **Client ID**: Copy this value
   - **Client Secret**: Generate and copy this value
   - **Callback URL**: `https://your-mcp-server.com/auth/callback`

### Step 3: Set Scopes and Permissions

For the MCP server, recommended scopes:
- `read:user` - Read user profile information (maps to `read` permission)
- `user:email` - Read user email address (maps to `read` permission)
- `read:org` - Read organization membership (maps to `read` permission)
- `repo` - Repository access for advanced features (maps to `write` permission)

### Step 4: Configure MCP Server

#### Helm Values Configuration

```yaml
# helm/values-github.yaml
auth:
  enabled: true
  oauth2:
    issuerUrl: "https://api.github.com"
    validScopes: "read:user,user:email,read:org,repo"
    defaultScopes: "read:user,user:email"
    requiredScopes: "read:user"
    clientRegistrationEnabled: true
    revocationEnabled: true
  createSecret:
    enabled: true
    clientId: "YOUR_GITHUB_CLIENT_ID"
    clientSecret: "YOUR_GITHUB_CLIENT_SECRET"

# GitHub-specific configuration
github:
  organization: "your-org-name"  # Optional: restrict to org members
  scopes:
    read: ["read:user", "user:email", "read:org"]
    write: ["repo"]
    admin: ["admin:org", "admin:repo_hook"]
```

#### Environment Variables

```bash
# .env file
ENABLE_AUTH=true
AUTH_PROVIDER=github
AUTH_ISSUER_URL=https://api.github.com
AUTH_AUDIENCE=your_github_client_id
AUTH_VALID_SCOPES=read:user,user:email,read:org,repo
AUTH_DEFAULT_SCOPES=read:user,user:email
AUTH_REQUIRED_SCOPES=read:user
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
GITHUB_ORG=your-organization  # Optional
```

### Step 5: Organization-Based Access Control (Optional)

To restrict access to members of a specific GitHub organization:

1. Set the `GITHUB_ORG` environment variable
2. Ensure your OAuth app has `read:org` scope
3. Users must be public members of the organization or grant organization access

```bash
# Restrict to organization members
export GITHUB_ORG=my-company
```

### GitHub Apps Alternative

For enhanced security, you can use GitHub Apps instead of OAuth Apps:

#### Create GitHub App

1. Go to **Organization Settings** → **Developer settings** → **GitHub Apps**
2. Click **New GitHub App**
3. Configure:
   - **GitHub App name**: `MCP Schema Registry`
   - **Homepage URL**: `https://your-mcp-server.com`
   - **Callback URL**: `https://your-mcp-server.com/auth/callback`
   - **Permissions**: 
     - Repository permissions: `Metadata: Read`
     - Organization permissions: `Members: Read`
     - Account permissions: `Email addresses: Read`

#### GitHub App Configuration

```bash
# .env file for GitHub Apps
ENABLE_AUTH=true
AUTH_PROVIDER=github
GITHUB_APP_ID=your_app_id
GITHUB_APP_PRIVATE_KEY_PATH=/path/to/private-key.pem
GITHUB_APP_INSTALLATION_ID=your_installation_id
```

### GitHub Scope Mapping

The MCP server maps GitHub scopes to internal permissions:

| GitHub Scope | MCP Permission | Description |
|--------------|----------------|-------------|
| `read:user` | `read` | Read user profile information |
| `user:email` | `read` | Access user email address |
| `read:org` | `read` | Read organization membership |
| `repo` | `write` | Repository access (implies schema write access) |
| `admin:org` | `admin` | Organization administration |
| `admin:repo_hook` | `admin` | Repository webhook administration |

### Testing GitHub OAuth

#### Test Token Validation

```bash
# Get GitHub personal access token for testing
GITHUB_TOKEN="ghp_your_personal_access_token"

# Test API access
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     https://api.github.com/user

# Test with MCP server
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     https://your-mcp-server.com/api/registries
```

#### Verify Organization Membership

```bash
# Check organization membership
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     https://api.github.com/user/orgs
```

## 🔧 Advanced Configuration

### Custom Scopes Mapping

You can customize how OAuth scopes map to MCP permissions:

```yaml
# Custom scope mapping in values.yaml
auth:
  oauth2:
    scopeMapping:
      read: ["openid", "email", "profile"]
      write: ["openid", "email", "profile", "schema:write"]
      admin: ["openid", "email", "profile", "schema:admin"]
```

### Multi-Provider Support

To support multiple OAuth providers simultaneously:

```yaml
# values-multi-provider.yaml
auth:
  multiProvider:
    enabled: true
    providers:
      azure:
        name: "Azure AD"
        issuerUrl: "https://login.microsoftonline.com/TENANT_ID/v2.0"
        clientId: "azure_client_id"
        clientSecret: "azure_client_secret"
      google:
        name: "Google"
        issuerUrl: "https://accounts.google.com"
        clientId: "google_client_id"
        clientSecret: "google_client_secret"
```

### Token Validation

For production deployments, implement proper JWT token validation:

```python
# Custom token validator
import jwt
from cryptography.x509 import load_pem_x509_certificate

async def validate_jwt_token(token: str, provider: str) -> Optional[Dict[str, Any]]:
    try:
        # Get public key from provider's JWKS endpoint
        jwks_url = f"{issuer_url}/.well-known/jwks.json"
        public_key = get_public_key_from_jwks(jwks_url, token)
        
        # Validate token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            audience=client_id,
            issuer=issuer_url
        )
        
        return payload
    except jwt.InvalidTokenError:
        return None
```

## 🧪 Testing OAuth Integration

### Development Testing

Use the provided development tokens for testing:

```bash
# Test with read-only access
curl -H "Authorization: Bearer dev-token-read" \
     https://your-mcp-server.com/api/subjects

# Test with write access
curl -H "Authorization: Bearer dev-token-read,write" \
     -X POST https://your-mcp-server.com/api/subjects/test \
     -d '{"schema": "..."}'

# Test with admin access
curl -H "Authorization: Bearer dev-token-read,write,admin" \
     -X DELETE https://your-mcp-server.com/api/subjects/test
```

### Production Testing

1. **Obtain real OAuth token**:
   ```bash
   # Example for testing with real token
   ACCESS_TOKEN=$(curl -X POST https://provider/oauth2/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=client_credentials&client_id=CLIENT_ID&client_secret=CLIENT_SECRET&scope=openid email profile" \
     | jq -r '.access_token')
   ```

2. **Test MCP endpoints**:
   ```bash
   curl -H "Authorization: Bearer $ACCESS_TOKEN" \
        https://your-mcp-server.com/api/registries
   ```

## 🔒 Security Best Practices

### 1. Client Secret Management
- Store secrets in Kubernetes secrets, not in values files
- Rotate secrets regularly
- Use different secrets for different environments

### 2. Token Validation
- Always validate JWT signatures
- Check token expiration
- Verify issuer and audience claims
- Implement proper error handling

### 3. Scope Management
- Use principle of least privilege
- Map OAuth scopes to specific MCP permissions
- Audit scope assignments regularly

### 4. Network Security
- Use HTTPS for all OAuth endpoints
- Implement proper CORS policies
- Use network policies in Kubernetes

## 🚨 Troubleshooting

### Common Issues

**1. Invalid redirect URI**
```bash
# Ensure redirect URI matches exactly in OAuth provider
# Check for trailing slashes, http vs https, port numbers
```

**2. Invalid client credentials**
```bash
# Verify client ID and secret are correct
# Check if client secret has expired
kubectl get secret -n kafka-tools oauth-secret -o yaml
```

**3. Scope issues**
```bash
# Check if required scopes are granted
# Verify scope mapping in configuration
kubectl logs -n kafka-tools deployment/kafka-schema-registry-mcp | grep scope
```

**4. Token validation failures**
```bash
# Check issuer URL is correct
# Verify public key retrieval from JWKS endpoint
# Check token expiration
```

### Debug Mode

Enable OAuth debug logging:

```yaml
# values.yaml
app:
  logLevel: "DEBUG"
auth:
  debug: true
```

## 📚 Additional Resources

- **Azure AD**: [Microsoft Identity Platform Documentation](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
- **Google OAuth**: [Google Identity Documentation](https://developers.google.com/identity)
- **Keycloak**: [Keycloak Documentation](https://www.keycloak.org/documentation)
- **Okta**: [Okta Developer Documentation](https://developer.okta.com/)
- **GitHub OAuth**: [GitHub OAuth Apps Documentation](https://docs.github.com/en/developers/apps/building-oauth-apps)
- **GitHub Apps**: [GitHub Apps Documentation](https://docs.github.com/en/developers/apps/building-github-apps)
- **OAuth 2.0**: [RFC 6749](https://tools.ietf.org/html/rfc6749)
- **OpenID Connect**: [OpenID Connect Specification](https://openid.net/connect/)

## 🎯 Next Steps

After configuring OAuth:

1. **Deploy MCP Server** with OAuth enabled
2. **Configure VSCode/IDE** with OAuth authentication
3. **Test all scope levels** (read, write, admin)
4. **Set up monitoring** for authentication events
5. **Configure audit logging** for security compliance
6. **Train users** on OAuth authentication flow

Happy secure schema management! 🔐🚀 