# Examples for Kafka Schema Registry MCP Server

This folder contains example scripts for testing, demonstrating, and manually validating features of the MCP server, especially around OAuth 2.1 authentication, user roles, and remote server connectivity.

## Contents

- [`test-jwt-validation.py`](./test-jwt-validation.py):
  - **Purpose:** Demonstrates how to validate JWT tokens using the **OAuth 2.1 generic discovery approach** that works with any OAuth 2.1 compliant provider (Azure AD, Google, Keycloak, Okta, GitHub, and custom providers).
  - **How to Run:**
    ```bash
    python test-jwt-validation.py [issuer_url] [audience] [jwt_token]
    ```
    - Examples:
      ```bash
      # Azure AD
      python test-jwt-validation.py "https://login.microsoftonline.com/tenant-id/v2.0" "your-client-id" "<your_jwt_token>"
      
      # Google OAuth 2.0
      python test-jwt-validation.py "https://accounts.google.com" "client-id.apps.googleusercontent.com" "<your_jwt_token>"
      
      # Any OAuth 2.1 Provider
      python test-jwt-validation.py "https://your-oauth-provider.com" "your-audience" "<your_jwt_token>"
      ```
    - Run without arguments to see comprehensive OAuth 2.1 configuration examples and provider setup guide.

- [`test-user-roles.py`](./test-user-roles.py):
  - **Purpose:** Shows how user roles and scopes are extracted from JWT tokens for different OAuth 2.1 providers, and how the MCP server interprets them for access control using the generic discovery approach.
  - **How to Run:**
    ```bash
    python test-user-roles.py
    ```
    - No arguments needed. Demonstrates OAuth 2.1 role extraction scenarios for various providers.

- [`test-remote-mcp.py`](./test-remote-mcp.py):
  - **Purpose:** Tests connectivity and functionality of a remote MCP server, including OAuth 2.1 authentication and tool/resource listing.
  - **How to Run:**
    ```bash
    python test-remote-mcp.py --url <MCP_SERVER_URL> [--auth-token <JWT_TOKEN>] [--verbose]
    ```
    - Example:
      ```bash
      python test-remote-mcp.py --url http://localhost:8000/mcp --auth-token "dev-token-read"
      ```

## 🚀 OAuth 2.1 Generic Discovery Features

These examples demonstrate the **major architectural improvement** in v2.0.0:

### **Before (Provider-Specific - v1.x)**
```bash
# Required 8+ variables per provider
export AUTH_PROVIDER=azure
export AZURE_TENANT_ID=your-tenant
export AZURE_CLIENT_ID=your-client-id
export AZURE_CLIENT_SECRET=your-client-secret
export AZURE_AUTHORITY=https://login.microsoftonline.com/your-tenant
# ... many more provider-specific variables
```

### **After (Generic OAuth 2.1 - v2.x)**
```bash
# Just 2 core variables for ANY provider!
export AUTH_ISSUER_URL="https://login.microsoftonline.com/your-tenant-id/v2.0"
export AUTH_AUDIENCE="your-azure-client-id"
```

### **Benefits:**
- **🚀 75% Configuration Reduction**: 2 variables instead of 8+ per provider
- **🔮 Future-Proof**: Works with any OAuth 2.1 compliant provider without code changes
- **🛡️ Enhanced Security**: OAuth 2.1 compliance with PKCE, Resource Indicators (RFC 8707)
- **🔧 Easier Maintenance**: No provider-specific bugs or configurations

## Notes

- These scripts demonstrate the **OAuth 2.1 generic discovery system** introduced in v2.0.0
- Scripts are intended for **manual testing, demonstration, and debugging** - not automated regression tests
- You may need to install additional dependencies (see the main project `requirements.txt`)
- For complete OAuth 2.1 setup guides, see **[docs/oauth-providers-guide.md](../docs/oauth-providers-guide.md)**
- For migration from provider-specific configurations, see **[docs/v2-migration-guide.md](../docs/v2-migration-guide.md)** 