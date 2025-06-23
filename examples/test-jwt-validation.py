#!/usr/bin/env python3
"""
JWT Validation Test for OAuth 2.1 Providers

This script demonstrates how to configure and test JWT token validation
using the generic OAuth 2.1 discovery approach that works with any
OAuth 2.1 compliant provider.

Usage:
    python examples/test-jwt-validation.py [issuer_url] [audience] [token]

Examples:
    python examples/test-jwt-validation.py "https://login.microsoftonline.com/tenant-id/v2.0" "your-client-id" "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..."
    python examples/test-jwt-validation.py "https://accounts.google.com" "client-id.apps.googleusercontent.com" "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE2NzA..."
    python examples/test-jwt-validation.py "https://your-domain.okta.com/oauth2/default" "api://your-api" "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..."
"""

import asyncio
import os
import sys

# Add parent directory to path to import oauth_provider
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables for testing
os.environ["ENABLE_AUTH"] = "true"


def setup_oauth21_config(issuer_url: str, audience: str):
    """Configure environment for OAuth 2.1 generic discovery."""
    os.environ.update(
        {
            "AUTH_ISSUER_URL": issuer_url,
            "AUTH_AUDIENCE": audience,
            "AUTH_VALID_SCOPES": "read,write,admin",
            "AUTH_DEFAULT_SCOPES": "read",
            "AUTH_REQUIRED_SCOPES": "read",
            "REQUIRE_PKCE": "true",
            "JWKS_CACHE_TTL": "300",  # 5 minutes for testing
        }
    )


async def test_jwt_validation(issuer_url: str, audience: str, token: str):
    """Test JWT validation using OAuth 2.1 generic discovery."""
    print(f"🚀 Testing OAuth 2.1 JWT Validation")
    print("=" * 60)

    try:
        from oauth_provider import JWT_AVAILABLE, KafkaSchemaRegistryOAuthProvider

        if not JWT_AVAILABLE:
            print("❌ JWT validation libraries not available")
            print("Install with: pip install PyJWT aiohttp cryptography")
            return False

        # Setup OAuth 2.1 generic configuration
        setup_oauth21_config(issuer_url, audience)

        # Initialize OAuth provider
        oauth_provider = KafkaSchemaRegistryOAuthProvider()

        # Test JWT validation
        print(f"📝 Token (first 50 chars): {token[:50]}...")
        print(f"🌐 Issuer URL: {issuer_url}")
        print(f"👥 Audience: {audience}")
        print(f"🔍 Discovery: Using OAuth 2.1 RFC 8414 discovery")
        print()

        # Validate the token
        result = await oauth_provider.validate_token(token)

        if result:
            print("✅ JWT validation successful!")
            print(f"👤 User: {result.get('sub', 'unknown')}")
            print(f"📧 Email: {result.get('email', 'not provided')}")
            print(f"🏷️  Name: {result.get('name', 'not provided')}")
            print(f"🔑 Scopes: {result.get('scopes', [])}")
            print(f"🏢 Issuer: {result.get('iss', 'unknown')}")
            print(f"⏰ Expires: {result.get('exp', 'unknown')}")

            # Test scope access levels
            user_scopes = set(result.get("scopes", []))
            print()
            print("🔒 Access Level Check:")
            print(
                f"   Read Access: {'✅' if oauth_provider.has_read_access(user_scopes) else '❌'}"
            )
            print(
                f"   Write Access: {'✅' if oauth_provider.has_write_access(user_scopes) else '❌'}"
            )
            print(
                f"   Admin Access: {'✅' if oauth_provider.has_admin_access(user_scopes) else '❌'}"
            )

            return True
        else:
            print("❌ JWT validation failed")
            print("Possible reasons:")
            print("   • Token expired")
            print("   • Invalid signature")
            print("   • Wrong issuer or audience")
            print("   • Malformed token")
            print("   • Network error fetching JWKS")
            print("   • OAuth 2.1 discovery failed")
            return False

    except ImportError:
        print("❌ OAuth provider not available (missing MCP auth modules)")
        return False
    except Exception as e:
        print(f"❌ Error during JWT validation: {e}")
        return False


def print_oauth21_examples():
    """Print OAuth 2.1 configuration examples for various providers."""
    print("🚀 OAuth 2.1 Generic Configuration Examples")
    print("=" * 60)

    examples = [
        {
            "name": "🟦 Azure AD / Entra ID",
            "issuer_url": "https://login.microsoftonline.com/your-tenant-id/v2.0",
            "audience": "your-azure-client-id",
            "description": "Microsoft's enterprise identity platform",
        },
        {
            "name": "🟨 Google OAuth 2.0",
            "issuer_url": "https://accounts.google.com",
            "audience": "your-client-id.apps.googleusercontent.com",
            "description": "Google's identity and access management",
        },
        {
            "name": "🟥 Keycloak",
            "issuer_url": "https://your-keycloak-server.com/realms/your-realm",
            "audience": "your-keycloak-client-id",
            "description": "Open-source identity and access management",
        },
        {
            "name": "🟧 Okta",
            "issuer_url": "https://your-domain.okta.com/oauth2/default",
            "audience": "api://your-api-identifier",
            "description": "Enterprise identity and access management",
        },
        {
            "name": "⚫ GitHub (Limited Support)",
            "issuer_url": "https://github.com",
            "audience": "your-github-client-id",
            "description": "GitHub OAuth with automatic fallback configuration",
        },
        {
            "name": "🟪 Any OAuth 2.1 Provider",
            "issuer_url": "https://your-oauth-provider.com",
            "audience": "your-client-id-or-api-identifier",
            "description": "Any RFC 8414 compliant OAuth 2.1 provider",
        },
    ]

    for example in examples:
        print(f"\n{example['name']} - {example['description']}")
        print(f"   Issuer URL: {example['issuer_url']}")
        print(f"   Audience: {example['audience']}")
        print(f"   Environment Variables:")
        print(f"     export AUTH_ISSUER_URL=\"{example['issuer_url']}\"")
        print(f"     export AUTH_AUDIENCE=\"{example['audience']}\"")


def print_oauth21_benefits():
    """Print the benefits of OAuth 2.1 generic discovery."""
    print("\n🎯 Benefits of OAuth 2.1 Generic Discovery")
    print("=" * 60)

    print(
        """
🚀 Simplified Configuration:
   - 75% fewer environment variables (2 vs 8+ per provider)
   - No provider-specific knowledge required
   - Universal configuration works with any OAuth 2.1 provider

🔮 Future-Proof Architecture:
   - New providers work automatically without code changes
   - Standards-based approach using RFC 8414 discovery
   - Automatic endpoint updates when providers change URLs

🛡️ Enhanced Security:
   - OAuth 2.1 compliance with PKCE, Resource Indicators
   - Automatic security feature detection from discovery metadata
   - Better token validation with proper audience checking

🔧 Easier Maintenance:
   - No provider-specific bugs to fix
   - Reduced complexity in codebase (~75% less provider code)
   - Self-healing configuration via discovery refresh
"""
    )


def print_production_deployment():
    """Print production deployment examples using OAuth 2.1."""
    print("\n🚀 Production Deployment Examples (OAuth 2.1)")
    print("=" * 60)

    print("\n📦 Docker Deployment:")
    print(
        """
# Azure AD
docker run -d \\
  -e ENABLE_AUTH=true \\
  -e AUTH_ISSUER_URL="https://login.microsoftonline.com/your-tenant-id/v2.0" \\
  -e AUTH_AUDIENCE="your-azure-client-id" \\
  -e AUTH_VALID_SCOPES="read,write,admin" \\
  -p 8000:8000 \\
  aywengo/kafka-schema-reg-mcp:stable

# Google OAuth 2.0
docker run -d \\
  -e ENABLE_AUTH=true \\
  -e AUTH_ISSUER_URL="https://accounts.google.com" \\
  -e AUTH_AUDIENCE="your-client-id.apps.googleusercontent.com" \\
  -e AUTH_VALID_SCOPES="read,write,admin" \\
  -p 8000:8000 \\
  aywengo/kafka-schema-reg-mcp:stable

# Any OAuth 2.1 Provider
docker run -d \\
  -e ENABLE_AUTH=true \\
  -e AUTH_ISSUER_URL="https://your-oauth-provider.com" \\
  -e AUTH_AUDIENCE="your-client-id-or-api-identifier" \\
  -e AUTH_VALID_SCOPES="read,write,admin" \\
  -p 8000:8000 \\
  aywengo/kafka-schema-reg-mcp:stable
"""
    )

    print("\n☸️  Kubernetes Deployment:")
    print(
        """
# Create secret with OAuth 2.1 configuration
kubectl create secret generic mcp-oauth21-config \\
  --from-literal=AUTH_ISSUER_URL="https://your-oauth-provider.com" \\
  --from-literal=AUTH_AUDIENCE="your-client-id"

# Deploy with Helm
helm upgrade --install mcp-server ./helm \\
  --set auth.enabled=true \\
  --set auth.oauth2.issuerUrl="https://your-oauth-provider.com" \\
  --set auth.oauth2.audience="your-client-id" \\
  --set-string auth.existingSecret.name=mcp-oauth21-config
"""
    )


def print_testing_guide():
    """Print testing guide for OAuth 2.1 JWT validation."""
    print("\n🧪 Testing Guide (OAuth 2.1)")
    print("=" * 60)

    print(
        """
1. **Test OAuth 2.1 Discovery:**
   
   # Test discovery endpoint
   curl https://your-oauth-provider.com/.well-known/oauth-authorization-server | jq
   
   # Test MCP server discovery
   curl http://localhost:8000/.well-known/oauth-authorization-server | jq

2. **Get a real JWT token from your OAuth 2.1 provider:**
   
   Azure AD:
   curl -X POST https://login.microsoftonline.com/TENANT_ID/oauth2/v2.0/token \\
     -H "Content-Type: application/x-www-form-urlencoded" \\
     -d "grant_type=client_credentials&client_id=CLIENT_ID&client_secret=CLIENT_SECRET&scope=your-client-id/.default"
   
   Google:
   # Use Google OAuth Playground: https://developers.google.com/oauthplayground
   
   Keycloak:
   curl -X POST https://keycloak.example.com/realms/your-realm/protocol/openid-connect/token \\
     -H "Content-Type: application/x-www-form-urlencoded" \\
     -d "grant_type=client_credentials&client_id=CLIENT_ID&client_secret=CLIENT_SECRET"
   
   Any OAuth 2.1 Provider:
   curl -X POST https://your-oauth-provider.com/token \\
     -H "Content-Type: application/x-www-form-urlencoded" \\
     -d "grant_type=client_credentials&client_id=CLIENT_ID&client_secret=CLIENT_SECRET&scope=your-scopes"

3. **Test JWT validation:**
   python examples/test-jwt-validation.py "https://your-oauth-provider.com" "your-audience" "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..."

4. **Use with MCP server:**
   curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
     http://localhost:8000/.well-known/oauth-protected-resource

5. **Debug issues:**
   - Check OAuth 2.1 discovery: /.well-known/oauth-authorization-server
   - Verify token expiration: jwt.io
   - Ensure issuer and audience match configuration
   - Check JWKS endpoint accessibility
   - Test with MCP discovery endpoint tool
"""
    )


async def main():
    """Main function to run OAuth 2.1 JWT validation tests."""
    if len(sys.argv) < 4:
        print("🚀 OAuth 2.1 JWT Validation Test")
        print("=" * 60)
        print("Usage: python test-jwt-validation.py [issuer_url] [audience] [token]")
        print()
        print("Examples:")
        print(
            '   python test-jwt-validation.py "https://login.microsoftonline.com/tenant-id/v2.0" "your-client-id" "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..."'
        )
        print(
            '   python test-jwt-validation.py "https://accounts.google.com" "client-id.apps.googleusercontent.com" "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE2NzA..."'
        )
        print(
            '   python test-jwt-validation.py "https://your-domain.okta.com/oauth2/default" "api://your-api" "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..."'
        )
        print()

        print_oauth21_examples()
        print_oauth21_benefits()
        print_production_deployment()
        print_testing_guide()
        return

    issuer_url = sys.argv[1]
    audience = sys.argv[2]
    token = sys.argv[3]

    # Test JWT validation
    success = await test_jwt_validation(issuer_url, audience, token)

    if success:
        print("\n🎉 OAuth 2.1 JWT validation test completed successfully!")
        print("Ready for production deployment with OAuth 2.1 generic discovery.")
    else:
        print("\n❌ OAuth 2.1 JWT validation test failed.")
        print("Check OAuth 2.1 discovery endpoint and token validity.")


if __name__ == "__main__":
    asyncio.run(main())
