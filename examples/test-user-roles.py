#!/usr/bin/env python3
"""
Test User Role Assignments

This script demonstrates how to test user role assignments for different OAuth providers.
It shows various JWT token formats and how the MCP server extracts scopes from them.

Usage:
    python examples/test-user-roles.py
"""

import os
import sys

# Add parent directory to path to import oauth_provider
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment to enable OAuth for testing
os.environ["ENABLE_AUTH"] = "true"
os.environ["AUTH_ISSUER_URL"] = "https://test-provider.com"
os.environ["AUTH_VALID_SCOPES"] = "read,write,admin"

try:
    from oauth_provider import KafkaSchemaRegistryOAuthProvider

    oauth_available = True
except ImportError:
    print(
        "⚠️  OAuth dependencies not available. Install MCP auth modules to test OAuth functionality."
    )
    print("This is normal in development mode. OAuth features will be disabled.")
    oauth_available = False

    # Create a mock provider for testing purposes
    class MockOAuthProvider:
        def __init__(self):
            self.valid_scopes = {"read", "write", "admin"}

        def extract_scopes_from_jwt(self, jwt_payload):
            # Simple mock implementation for testing
            scopes = []
            if "roles" in jwt_payload:
                scopes.extend(jwt_payload["roles"])
            if "scope" in jwt_payload:
                scopes.extend(jwt_payload["scope"].split())
            return {**jwt_payload, "scopes": list(set(scopes))}

        def has_read_access(self, user_scopes):
            return "read" in user_scopes

        def has_write_access(self, user_scopes):
            return "write" in user_scopes and "read" in user_scopes

        def has_admin_access(self, user_scopes):
            return (
                "admin" in user_scopes
                and "write" in user_scopes
                and "read" in user_scopes
            )

        async def validate_token(self, token):
            if token.startswith("dev-token-"):
                scopes_str = token.replace("dev-token-", "")
                scopes = [s.strip() for s in scopes_str.split(",") if s.strip()]
                return {"sub": "test-user", "scopes": scopes}
            return None

    KafkaSchemaRegistryOAuthProvider = MockOAuthProvider


def test_azure_ad_roles():
    """Test Azure AD role-based JWT tokens"""
    print("🔵 Testing Azure AD Roles")
    print("=" * 50)

    # Azure AD token with roles claim
    azure_token_payload = {
        "sub": "john.doe@company.com",
        "name": "John Doe",
        "roles": ["read", "write"],  # Azure app roles
        "iss": "https://login.microsoftonline.com/tenant-id/v2.0",
        "aud": "api://mcp-schema-registry",
        "exp": 1640995200,
        "iat": 1640991600,
    }

    provider = KafkaSchemaRegistryOAuthProvider()
    result = provider.extract_scopes_from_jwt(azure_token_payload)

    print(f"✅ User: {result['name']}")
    print(f"✅ Email: {result['sub']}")
    print(f"✅ Assigned Roles: {azure_token_payload['roles']}")
    print(f"✅ Extracted Scopes: {result['scopes']}")
    print(f"✅ Has Read Access: {provider.has_read_access(set(result['scopes']))}")
    print(f"✅ Has Write Access: {provider.has_write_access(set(result['scopes']))}")
    print(f"✅ Has Admin Access: {provider.has_admin_access(set(result['scopes']))}")
    print()


def test_google_groups():
    """Test Google OAuth with group membership"""
    print("🟢 Testing Google Groups")
    print("=" * 50)

    # Google token with group membership
    google_token_payload = {
        "sub": "jane.smith@company.com",
        "name": "Jane Smith",
        "email": "jane.smith@company.com",
        "groups": ["mcp-readers@company.com", "mcp-writers@company.com"],
        "iss": "https://accounts.google.com",
        "aud": "your-google-client-id.apps.googleusercontent.com",
        "exp": 1640995200,
        "iat": 1640991600,
    }

    provider = KafkaSchemaRegistryOAuthProvider()
    result = provider.extract_scopes_from_jwt(google_token_payload)

    print(f"✅ User: {result['name']}")
    print(f"✅ Email: {result['email']}")
    print(f"✅ Group Membership: {google_token_payload['groups']}")
    print(f"✅ Extracted Scopes: {result['scopes']}")
    print(f"✅ Has Read Access: {provider.has_read_access(set(result['scopes']))}")
    print(f"✅ Has Write Access: {provider.has_write_access(set(result['scopes']))}")
    print(f"✅ Has Admin Access: {provider.has_admin_access(set(result['scopes']))}")
    print()


def test_keycloak_realm_roles():
    """Test Keycloak with realm roles"""
    print("🟣 Testing Keycloak Realm Roles")
    print("=" * 50)

    # Keycloak token with realm roles
    keycloak_token_payload = {
        "sub": "admin-user-123",
        "preferred_username": "admin",
        "name": "System Administrator",
        "realm_access": {
            "roles": ["mcp-admin", "mcp-writer", "mcp-reader", "offline_access"]
        },
        "resource_access": {"mcp-client": {"roles": ["mcp-admin"]}},
        "iss": "https://keycloak.company.com/realms/production",
        "aud": "mcp-client",
        "exp": 1640995200,
        "iat": 1640991600,
    }

    provider = KafkaSchemaRegistryOAuthProvider()
    result = provider.extract_scopes_from_jwt(keycloak_token_payload)

    print(f"✅ User: {result['preferred_username']}")
    print(f"✅ Display Name: {result['name']}")
    print(f"✅ Realm Roles: {keycloak_token_payload['realm_access']['roles']}")
    print(f"✅ Extracted Scopes: {result['scopes']}")
    print(f"✅ Has Read Access: {provider.has_read_access(set(result['scopes']))}")
    print(f"✅ Has Write Access: {provider.has_write_access(set(result['scopes']))}")
    print(f"✅ Has Admin Access: {provider.has_admin_access(set(result['scopes']))}")
    print()


def test_okta_custom_attributes():
    """Test Okta with custom user attributes"""
    print("🟠 Testing Okta Custom Attributes")
    print("=" * 50)

    # Okta token with custom mcp_scopes attribute
    okta_token_payload = {
        "sub": "reader-user-456",
        "name": "Read Only User",
        "email": "readonly@company.com",
        "mcp_scopes": ["read"],  # Custom attribute
        "groups": ["Everyone", "IT-Team"],
        "iss": "https://company.okta.com/oauth2/default",
        "aud": "api://mcp-schema-registry",
        "exp": 1640995200,
        "iat": 1640991600,
    }

    provider = KafkaSchemaRegistryOAuthProvider()
    result = provider.extract_scopes_from_jwt(okta_token_payload)

    print(f"✅ User: {result['name']}")
    print(f"✅ Email: {result['email']}")
    print(f"✅ Custom MCP Scopes: {okta_token_payload['mcp_scopes']}")
    print(f"✅ Extracted Scopes: {result['scopes']}")
    print(f"✅ Has Read Access: {provider.has_read_access(set(result['scopes']))}")
    print(f"✅ Has Write Access: {provider.has_write_access(set(result['scopes']))}")
    print(f"✅ Has Admin Access: {provider.has_admin_access(set(result['scopes']))}")
    print()


def test_scope_hierarchy():
    """Test scope hierarchy enforcement"""
    print("🔄 Testing Scope Hierarchy")
    print("=" * 50)

    provider = KafkaSchemaRegistryOAuthProvider()

    # Test admin user gets all scopes
    admin_payload = {"sub": "admin", "scope": "admin"}
    admin_result = provider.extract_scopes_from_jwt(admin_payload)
    print(f"✅ Admin user scopes: {admin_result['scopes']}")

    # Test write user gets read too
    writer_payload = {"sub": "writer", "scope": "write"}
    writer_result = provider.extract_scopes_from_jwt(writer_payload)
    print(f"✅ Writer user scopes: {writer_result['scopes']}")

    # Test read user only gets read
    reader_payload = {"sub": "reader", "scope": "read"}
    reader_result = provider.extract_scopes_from_jwt(reader_payload)
    print(f"✅ Reader user scopes: {reader_result['scopes']}")
    print()


def test_development_tokens():
    """Test development token format"""
    print("🧪 Testing Development Tokens")
    print("=" * 50)

    import asyncio

    async def test_dev_tokens():
        provider = KafkaSchemaRegistryOAuthProvider()

        # Test different development token formats
        tokens = {
            "Read Only": "dev-token-read",
            "Read + Write": "dev-token-read,write",
            "Full Admin": "dev-token-read,write,admin",
            "Invalid": "dev-token-invalid-scope",
        }

        for desc, token in tokens.items():
            result = await provider.validate_token(token)
            if result:
                print(f"✅ {desc}: {result['scopes']}")
            else:
                print(f"❌ {desc}: Invalid token")

    asyncio.run(test_dev_tokens())
    print()


def main():
    """Run all user role assignment tests"""
    print("🔐 MCP Server - User Role Assignment Tests")
    print("=" * 60)
    print("Testing how different OAuth providers assign roles to users")
    print("=" * 60)
    print()

    # Test each OAuth provider
    test_azure_ad_roles()
    test_google_groups()
    test_keycloak_realm_roles()
    test_okta_custom_attributes()

    # Test system features
    test_scope_hierarchy()
    test_development_tokens()

    print("🎉 All tests completed!")
    print()
    print("Next Steps:")
    print("1. Choose your OAuth provider (Azure AD, Google, Keycloak, or Okta)")
    print("2. Follow the setup guide in docs/user-role-assignment-guide.md")
    print("3. Configure your users with appropriate roles/scopes")
    print("4. Deploy with OAuth enabled using Helm charts")
    print("5. Test with real JWT tokens from your provider")


if __name__ == "__main__":
    main()
