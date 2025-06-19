#!/usr/bin/env python3
"""
JWT Validation Test for OAuth Providers

This script demonstrates how to configure and test JWT token validation
for Azure AD, Google, Keycloak, and Okta providers.

Usage:
    python examples/test-jwt-validation.py [provider] [token]

Examples:
    python examples/test-jwt-validation.py azure "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..."
    python examples/test-jwt-validation.py google "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE2NzA..."
    python examples/test-jwt-validation.py auto "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..."
"""

import asyncio
import json
import os
import sys

# Add parent directory to path to import oauth_provider
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables for testing
os.environ["ENABLE_AUTH"] = "true"


def setup_azure_config():
    """Configure environment for Azure AD JWT validation."""
    os.environ.update(
        {
            "AUTH_PROVIDER": "azure",
            "AUTH_ISSUER_URL": "https://login.microsoftonline.com/your-tenant-id/v2.0",
            "AZURE_TENANT_ID": "your-tenant-id",
            "AUTH_AUDIENCE": "api://your-app-id",
            "AUTH_VALID_SCOPES": "read,write,admin",
        }
    )


def setup_google_config():
    """Configure environment for Google OAuth JWT validation."""
    os.environ.update(
        {
            "AUTH_PROVIDER": "google",
            "AUTH_ISSUER_URL": "https://accounts.google.com",
            "AUTH_AUDIENCE": "your-client-id.apps.googleusercontent.com",
            "AUTH_VALID_SCOPES": "read,write,admin",
        }
    )


def setup_keycloak_config():
    """Configure environment for Keycloak JWT validation."""
    os.environ.update(
        {
            "AUTH_PROVIDER": "keycloak",
            "AUTH_ISSUER_URL": "https://keycloak.company.com/realms/production",
            "KEYCLOAK_REALM": "production",
            "AUTH_AUDIENCE": "mcp-client",
            "AUTH_VALID_SCOPES": "read,write,admin",
        }
    )


def setup_okta_config():
    """Configure environment for Okta JWT validation."""
    os.environ.update(
        {
            "AUTH_PROVIDER": "okta",
            "AUTH_ISSUER_URL": "https://your-domain.okta.com/oauth2/default",
            "OKTA_DOMAIN": "your-domain.okta.com",
            "AUTH_AUDIENCE": "api://mcp-schema-registry",
            "AUTH_VALID_SCOPES": "read,write,admin",
        }
    )


def setup_auto_config():
    """Configure environment for automatic provider detection."""
    os.environ.update(
        {
            "AUTH_PROVIDER": "auto",
            "AUTH_VALID_SCOPES": "read,write,admin",
            "JWKS_CACHE_TTL": "300",  # 5 minutes for testing
        }
    )


async def test_jwt_validation(provider: str, token: str):
    """Test JWT validation for a specific provider."""
    print(f"🔐 Testing JWT Validation for {provider.upper()}")
    print("=" * 60)

    try:
        from oauth_provider import JWT_AVAILABLE, KafkaSchemaRegistryOAuthProvider

        if not JWT_AVAILABLE:
            print("❌ JWT validation libraries not available")
            print("Install with: pip install PyJWT aiohttp cryptography")
            return False

        # Setup provider-specific configuration
        if provider == "azure":
            setup_azure_config()
        elif provider == "google":
            setup_google_config()
        elif provider == "keycloak":
            setup_keycloak_config()
        elif provider == "okta":
            setup_okta_config()
        elif provider == "auto":
            setup_auto_config()
        else:
            print(f"❌ Unknown provider: {provider}")
            return False

        # Initialize OAuth provider
        oauth_provider = KafkaSchemaRegistryOAuthProvider()

        # Test JWT validation
        print(f"📝 Token (first 50 chars): {token[:50]}...")
        print(f"🔧 Provider: {os.getenv('AUTH_PROVIDER')}")
        print(f"🌐 Issuer: {os.getenv('AUTH_ISSUER_URL')}")
        print(f"👥 Audience: {os.getenv('AUTH_AUDIENCE')}")
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
            return False

    except ImportError:
        print("❌ OAuth provider not available (missing MCP auth modules)")
        return False
    except Exception as e:
        print(f"❌ Error during JWT validation: {e}")
        return False


def print_configuration_examples():
    """Print configuration examples for each provider."""
    print("🔧 JWT Validation Configuration Examples")
    print("=" * 60)

    examples = {
        "Azure AD": {
            "AUTH_PROVIDER": "azure",
            "AZURE_TENANT_ID": "your-tenant-id",
            "AUTH_ISSUER_URL": "https://login.microsoftonline.com/your-tenant-id/v2.0",
            "AUTH_AUDIENCE": "api://your-app-id",
            "AUTH_VALID_SCOPES": "read,write,admin",
        },
        "Google OAuth": {
            "AUTH_PROVIDER": "google",
            "AUTH_ISSUER_URL": "https://accounts.google.com",
            "AUTH_AUDIENCE": "your-client-id.apps.googleusercontent.com",
            "AUTH_VALID_SCOPES": "read,write,admin",
        },
        "Keycloak": {
            "AUTH_PROVIDER": "keycloak",
            "AUTH_ISSUER_URL": "https://keycloak.company.com/realms/production",
            "KEYCLOAK_REALM": "production",
            "AUTH_AUDIENCE": "mcp-client",
            "AUTH_VALID_SCOPES": "read,write,admin",
        },
        "Okta": {
            "AUTH_PROVIDER": "okta",
            "OKTA_DOMAIN": "your-domain.okta.com",
            "AUTH_ISSUER_URL": "https://your-domain.okta.com/oauth2/default",
            "AUTH_AUDIENCE": "api://mcp-schema-registry",
            "AUTH_VALID_SCOPES": "read,write,admin",
        },
    }

    for provider, config in examples.items():
        print(f"\n🔵 {provider} Configuration:")
        for key, value in config.items():
            print(f"   export {key}={value}")


def print_production_deployment():
    """Print production deployment examples."""
    print("\n🚀 Production Deployment Examples")
    print("=" * 60)

    print("\n📦 Docker Deployment:")
    print(
        """
docker run -d \\
  -e ENABLE_AUTH=true \\
  -e AUTH_PROVIDER=azure \\
  -e AZURE_TENANT_ID=your-tenant-id \\
  -e AUTH_AUDIENCE=api://your-app-id \\
  -e AUTH_VALID_SCOPES=read,write,admin \\
  -p 8000:8000 \\
  aywengo/kafka-schema-reg-mcp:stable
"""
    )

    print("\n☸️  Kubernetes Deployment:")
    print(
        """
# Create secret with OAuth configuration
kubectl create secret generic mcp-oauth-config \\
  --from-literal=AUTH_PROVIDER=azure \\
  --from-literal=AZURE_TENANT_ID=your-tenant-id \\
  --from-literal=AUTH_AUDIENCE=api://your-app-id

# Deploy with Helm
helm upgrade --install mcp-server ./helm \\
  --set oauth.enabled=true \\
  --set oauth.provider=azure \\
  --set-string oauth.configSecret=mcp-oauth-config
"""
    )


def print_testing_guide():
    """Print testing guide for JWT validation."""
    print("\n🧪 Testing Guide")
    print("=" * 60)

    print(
        """
1. **Get a real JWT token from your OAuth provider:**
   
   Azure AD:
   curl -X POST https://login.microsoftonline.com/TENANT_ID/oauth2/v2.0/token \\
     -H "Content-Type: application/x-www-form-urlencoded" \\
     -d "grant_type=client_credentials&client_id=CLIENT_ID&client_secret=CLIENT_SECRET&scope=api://your-app-id/.default"
   
   Google:
   Use Google OAuth Playground: https://developers.google.com/oauthplayground
   
   Keycloak:
   curl -X POST https://keycloak.company.com/realms/production/protocol/openid-connect/token \\
     -H "Content-Type: application/x-www-form-urlencoded" \\
     -d "grant_type=client_credentials&client_id=CLIENT_ID&client_secret=CLIENT_SECRET"
   
   Okta:
   curl -X POST https://your-domain.okta.com/oauth2/default/v1/token \\
     -H "Content-Type: application/x-www-form-urlencoded" \\
     -d "grant_type=client_credentials&client_id=CLIENT_ID&client_secret=CLIENT_SECRET&scope=api://mcp-schema-registry"

2. **Test JWT validation:**
   python examples/test-jwt-validation.py azure "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..."

3. **Use with MCP server:**
   curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
     http://localhost:8000/mcp/tools/list_subjects

4. **Debug issues:**
   - Check token expiration: jwt.io
   - Verify issuer and audience match configuration
   - Ensure JWKS endpoint is accessible
   - Check network connectivity and firewalls
"""
    )


async def main():
    """Main function to run JWT validation tests."""
    if len(sys.argv) < 2:
        print("🔐 JWT Validation Test for OAuth Providers")
        print("=" * 60)
        print("Usage: python test-jwt-validation.py [provider] [token]")
        print()
        print("Providers: azure, google, keycloak, okta, auto")
        print()
        print("Examples:")
        print(
            '   python test-jwt-validation.py azure "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..."'
        )
        print(
            '   python test-jwt-validation.py auto "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE2NzA..."'
        )
        print()

        print_configuration_examples()
        print_production_deployment()
        print_testing_guide()
        return

    provider = sys.argv[1].lower()

    if len(sys.argv) < 3:
        print(f"❌ Missing JWT token for {provider} provider")
        print(f'Usage: python test-jwt-validation.py {provider} "YOUR_JWT_TOKEN"')
        return

    token = sys.argv[2]

    # Test JWT validation
    success = await test_jwt_validation(provider, token)

    if success:
        print("\n🎉 JWT validation test completed successfully!")
        print("Ready for production deployment with real JWT tokens.")
    else:
        print("\n❌ JWT validation test failed.")
        print("Check configuration and token validity.")


if __name__ == "__main__":
    asyncio.run(main())
