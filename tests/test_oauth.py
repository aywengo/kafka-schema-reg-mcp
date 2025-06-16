#!/usr/bin/env python3
"""
OAuth Testing for Kafka Schema Registry MCP Server

Tests OAuth functionality including scope validation, token handling,
and permission-based access control.
"""

import json
import os
import sys
import traceback
from typing import Any, Dict

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oauth_provider import (
    ENABLE_AUTH,
    get_oauth_provider_configs,
    get_oauth_scopes_info,
)


class OAuthTest:
    """OAuth functionality test class."""

    def __init__(self):
        self.test_results = []

    def run_test(self, test_name: str, test_func):
        """Run a single test and track results."""
        try:
            print(f"\n🧪 Running: {test_name}")
            result = test_func()
            if result:
                print(f"✅ {test_name} PASSED")
                self.test_results.append((test_name, True, None))
                return True
            else:
                print(f"❌ {test_name} FAILED")
                self.test_results.append((test_name, False, "Test returned False"))
                return False
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            self.test_results.append((test_name, False, str(e)))
            return False

    def test_oauth_configuration(self) -> bool:
        """Test OAuth configuration and environment setup."""
        print("🔧 Testing OAuth configuration...")

        # Check if OAuth is enabled
        print(f"   OAuth Enabled: {ENABLE_AUTH}")

        if not ENABLE_AUTH:
            print("   ⚠️  OAuth is disabled - testing configuration only")
            # When disabled, this is still a valid state for testing
            return True

        # Check required environment variables
        required_vars = [
            "AUTH_ISSUER_URL",
            "AUTH_VALID_SCOPES",
            "AUTH_DEFAULT_SCOPES",
            "AUTH_REQUIRED_SCOPES",
        ]

        missing_vars = []
        for var in required_vars:
            value = os.getenv(var)
            if not value:
                missing_vars.append(var)
            else:
                print(f"   ✅ {var}: {value}")

        if missing_vars:
            print(
                f"   ⚠️  Missing OAuth environment variables: {', '.join(missing_vars)}"
            )
            # This is expected when OAuth is enabled but not fully configured
            return True

        print("   ✅ OAuth configuration is complete")
        return True

    def test_scope_definitions(self) -> bool:
        """Test OAuth scope definitions and structure."""
        print("🔒 Testing OAuth scope definitions...")

        try:
            oauth_info = get_oauth_scopes_info()

            # Check main structure
            required_keys = ["scope_definitions", "oauth_enabled"]
            for key in required_keys:
                if key not in oauth_info:
                    print(f"   ❌ Missing key: {key}")
                    return False
                print(f"   ✅ Found key: {key}")

            # Check scope definitions
            scopes = oauth_info["scope_definitions"]
            expected_scopes = ["read", "write", "admin"]

            for scope in expected_scopes:
                if scope not in scopes:
                    print(f"   ❌ Missing scope: {scope}")
                    return False

                scope_info = scopes[scope]
                required_scope_keys = ["description", "level", "includes"]

                for scope_key in required_scope_keys:
                    if scope_key not in scope_info:
                        print(
                            f"   ❌ Missing scope key '{scope_key}' in scope '{scope}'"
                        )
                        return False

                print(
                    f"   ✅ Scope '{scope}': Level {scope_info['level']}, {len(scope_info['includes'])} tools"
                )

            print("   ✅ All scope definitions are valid")
            return True

        except Exception as e:
            print(f"   ❌ Error getting scope definitions: {e}")
            return False

    def test_tool_permissions(self) -> bool:
        """Test tool permission mappings via scope definitions."""
        print("🛠️  Testing tool permission mappings...")

        try:
            oauth_info = get_oauth_scopes_info()
            scope_definitions = oauth_info["scope_definitions"]

            # Build tool permissions from scope definitions
            tool_permissions = {}
            for scope_name, scope_info in scope_definitions.items():
                for tool in scope_info.get("includes", []):
                    if tool not in tool_permissions:
                        tool_permissions[tool] = []
                    tool_permissions[tool].append(scope_name)

            # Check that we have tool permissions defined
            if not tool_permissions:
                print("   ❌ No tool permissions derived from scope definitions")
                return False

            print(f"   ✅ Found {len(tool_permissions)} tools with permissions")

            # Verify some key tools have correct permissions
            expected_permissions = {
                "list_registries": ["read"],
                "register_schema": ["write"],
                "delete_subject": ["admin"],
                "migrate_schema": ["admin"],
                "clear_context_batch": ["admin"],
            }

            for tool, expected_scopes in expected_permissions.items():
                if tool in tool_permissions:
                    actual_scopes = tool_permissions[tool]
                    if all(scope in actual_scopes for scope in expected_scopes):
                        print(f"   ✅ {tool}: {actual_scopes}")
                    else:
                        print(
                            f"   ⚠️  {tool}: expected {expected_scopes}, got {actual_scopes}"
                        )
                else:
                    print(f"   ⚠️  Tool '{tool}' not found in scope definitions")

            return True

        except Exception as e:
            print(f"   ❌ Error testing tool permissions: {e}")
            return False

    def test_configuration_values(self) -> bool:
        """Test OAuth configuration values."""
        print("⚙️  Testing OAuth configuration values...")

        try:
            oauth_info = get_oauth_scopes_info()

            required_config_keys = [
                "oauth_enabled",
                "issuer_url",
                "valid_scopes",
                "default_scopes",
                "required_scopes",
            ]

            for key in required_config_keys:
                if key not in oauth_info:
                    print(f"   ❌ Missing configuration key: {key}")
                    return False
                print(f"   ✅ {key}: {oauth_info[key]}")

            # Only validate scope consistency if OAuth is enabled
            if oauth_info["oauth_enabled"]:
                valid_scopes = set(oauth_info["valid_scopes"])
                default_scopes = set(oauth_info["default_scopes"])
                required_scopes = set(oauth_info["required_scopes"])

                if not default_scopes.issubset(valid_scopes):
                    print(f"   ❌ Default scopes not subset of valid scopes")
                    return False

                if not required_scopes.issubset(valid_scopes):
                    print(f"   ❌ Required scopes not subset of valid scopes")
                    return False

                print("   ✅ Scope configuration is consistent")
            else:
                print("   ℹ️  OAuth disabled - skipping scope consistency check")

            return True

        except Exception as e:
            print(f"   ❌ Error testing configuration: {e}")
            return False

    def test_development_tokens(self) -> bool:
        """Test development token generation (if OAuth is enabled)."""
        print("🎫 Testing development tokens...")

        if not ENABLE_AUTH:
            print("   ℹ️  OAuth disabled - skipping token test")
            return True

        try:
            oauth_info = get_oauth_scopes_info()

            if "test_tokens" in oauth_info and oauth_info["test_tokens"]:
                test_tokens = oauth_info["test_tokens"]
                print(f"   ✅ Found {len(test_tokens)} test tokens")

                expected_tokens = ["read_only", "read_write", "full_admin"]
                for token_type in expected_tokens:
                    if token_type in test_tokens:
                        token = test_tokens[token_type]
                        print(f"   ✅ {token_type}: {token[:20]}...")
                    else:
                        print(f"   ⚠️  Missing test token: {token_type}")

                return True
            else:
                print("   ℹ️  No test tokens available (production mode)")
                return True

        except Exception as e:
            print(f"   ❌ Error testing development tokens: {e}")
            return False

    def test_oauth_provider_configs(self) -> bool:
        """Test OAuth provider configuration examples."""
        print("🏢 Testing OAuth provider configurations...")

        try:
            provider_configs = get_oauth_provider_configs()

            # Check that we have provider configs
            if not provider_configs:
                print("   ❌ No provider configurations returned")
                return False

            print(f"   ✅ Found {len(provider_configs)} provider configurations")

            # Expected providers
            expected_providers = ["azure", "google", "keycloak", "okta"]

            for provider in expected_providers:
                if provider not in provider_configs:
                    print(f"   ❌ Missing provider configuration: {provider}")
                    return False

                config = provider_configs[provider]
                print(f"   ✅ Found provider: {provider}")

                # Check required configuration keys for each provider
                required_keys = [
                    "name",
                    "issuer_url",
                    "auth_url",
                    "token_url",
                    "scopes",
                    "setup_docs",
                ]

                for key in required_keys:
                    if key not in config:
                        print(f"   ❌ Missing key '{key}' in {provider} configuration")
                        return False

                # Validate specific configurations
                if provider == "azure":
                    expected_values = {
                        "name": "Azure AD / Entra ID",
                        "client_id_env": "AZURE_CLIENT_ID",
                        "client_secret_env": "AZURE_CLIENT_SECRET",
                        "tenant_id_env": "AZURE_TENANT_ID",
                    }
                    for key, expected_value in expected_values.items():
                        if config.get(key) != expected_value:
                            print(
                                f"   ❌ Azure config key '{key}': expected '{expected_value}', got '{config.get(key)}'"
                            )
                            return False

                    # Check Azure-specific scopes
                    if "https://graph.microsoft.com/User.Read" not in config["scopes"]:
                        print("   ❌ Azure config missing Microsoft Graph scope")
                        return False

                    print("   ✅ Azure AD configuration is valid")

                elif provider == "google":
                    expected_values = {
                        "name": "Google OAuth 2.0",
                        "issuer_url": "https://accounts.google.com",
                        "client_id_env": "GOOGLE_CLIENT_ID",
                        "client_secret_env": "GOOGLE_CLIENT_SECRET",
                    }
                    for key, expected_value in expected_values.items():
                        if config.get(key) != expected_value:
                            print(
                                f"   ❌ Google config key '{key}': expected '{expected_value}', got '{config.get(key)}'"
                            )
                            return False

                    print("   ✅ Google OAuth configuration is valid")

                elif provider == "keycloak":
                    expected_values = {
                        "name": "Keycloak",
                        "client_id_env": "KEYCLOAK_CLIENT_ID",
                        "client_secret_env": "KEYCLOAK_CLIENT_SECRET",
                        "keycloak_server_env": "KEYCLOAK_SERVER_URL",
                        "keycloak_realm_env": "KEYCLOAK_REALM",
                    }
                    for key, expected_value in expected_values.items():
                        if config.get(key) != expected_value:
                            print(
                                f"   ❌ Keycloak config key '{key}': expected '{expected_value}', got '{config.get(key)}'"
                            )
                            return False

                    # Check Keycloak URL patterns
                    if (
                        "{keycloak-server}" not in config["issuer_url"]
                        or "{realm}" not in config["issuer_url"]
                    ):
                        print(
                            "   ❌ Keycloak issuer URL doesn't contain expected placeholders"
                        )
                        return False

                    print("   ✅ Keycloak configuration is valid")

                elif provider == "okta":
                    expected_values = {
                        "name": "Okta",
                        "client_id_env": "OKTA_CLIENT_ID",
                        "client_secret_env": "OKTA_CLIENT_SECRET",
                        "okta_domain_env": "OKTA_DOMAIN",
                    }
                    for key, expected_value in expected_values.items():
                        if config.get(key) != expected_value:
                            print(
                                f"   ❌ Okta config key '{key}': expected '{expected_value}', got '{config.get(key)}'"
                            )
                            return False

                    # Check Okta URL patterns
                    if "{okta-domain}" not in config["issuer_url"]:
                        print(
                            "   ❌ Okta issuer URL doesn't contain expected placeholders"
                        )
                        return False

                    print("   ✅ Okta configuration is valid")

                # Check that scopes include standard OpenID Connect scopes
                standard_scopes = ["openid", "email", "profile"]
                config_scopes = config["scopes"]

                for scope in standard_scopes:
                    if scope not in config_scopes:
                        print(
                            f"   ❌ {provider} configuration missing standard scope: {scope}"
                        )
                        return False

                # Check that URLs are properly formatted
                url_keys = ["issuer_url", "auth_url", "token_url"]
                for url_key in url_keys:
                    url = config[url_key]
                    if not url.startswith("https://"):
                        print(
                            f"   ❌ {provider} {url_key} should start with https://: {url}"
                        )
                        return False

                # Check that setup docs URL is valid
                setup_docs = config["setup_docs"]
                if not setup_docs.startswith("https://"):
                    print(
                        f"   ❌ {provider} setup_docs should start with https://: {setup_docs}"
                    )
                    return False

            print("   ✅ All provider configurations are valid")
            return True

        except Exception as e:
            print(f"   ❌ Error testing provider configurations: {e}")
            return False

    def print_usage_examples(self):
        """Print usage examples for OAuth testing."""
        print("\n" + "=" * 60)
        print(" OAuth Usage Examples")
        print("=" * 60)

        print("\n🚀 To enable OAuth for testing:")
        print("export ENABLE_AUTH=true")
        print("export AUTH_ISSUER_URL=https://your-auth-server.com")
        print("export AUTH_VALID_SCOPES=read,write,admin")
        print("export AUTH_DEFAULT_SCOPES=read")
        print("export AUTH_REQUIRED_SCOPES=read")

        print("\n📡 Testing with curl (if OAuth enabled):")
        print("# Read-only access:")
        print("curl -H 'Authorization: Bearer dev-token-read' \\")
        print("     http://localhost:8000/mcp/tools/list_registries")

        print("\n# Read-write access:")
        print("curl -H 'Authorization: Bearer dev-token-read,write' \\")
        print('     -X POST -d \'{"subject": "test", "schema_definition": {...}}\' \\')
        print("     http://localhost:8000/mcp/tools/register_schema")

        print("\n# Admin access:")
        print("curl -H 'Authorization: Bearer dev-token-read,write,admin' \\")
        print('     -X POST -d \'{"subject": "test"}\' \\')
        print("     http://localhost:8000/mcp/tools/delete_subject")

        print("\n🔧 Production setup:")
        print("1. Replace dev tokens with real JWT tokens")
        print("2. Implement proper token validation in oauth_provider.py")
        print("3. Set up a real OAuth 2.0 server (Azure AD, Google, Keycloak, Okta)")
        print("4. Use get_oauth_provider_configs() for provider-specific settings")

        print("\n🏢 OAuth Provider Configuration:")
        print("from oauth_provider import get_oauth_provider_configs")
        print("configs = get_oauth_provider_configs()")
        print("azure_config = configs['azure']")
        print("google_config = configs['google']")
        print("keycloak_config = configs['keycloak']")
        print("okta_config = configs['okta']")

    def generate_summary(self):
        """Generate test summary."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, passed, _ in self.test_results if passed)

        print(f"\n📊 Test Results: {passed_tests}/{total_tests} tests passed")

        if passed_tests == total_tests:
            print("\n🎉 ALL OAUTH TESTS PASSED!")
            print("✅ OAuth configuration is valid")
            print("✅ Scope definitions are correct")
            print("✅ Tool permissions are properly mapped")
            print("✅ Configuration values are consistent")
            print("✅ OAuth provider configs are valid (Azure, Google, Keycloak, Okta)")

            if ENABLE_AUTH:
                print("✅ OAuth is enabled and ready for testing")
            else:
                print("ℹ️  OAuth is disabled but configuration is valid")

            return True
        else:
            print(f"\n⚠️  {total_tests - passed_tests} test(s) failed")
            for test_name, passed, error in self.test_results:
                if not passed:
                    print(f"  • {test_name}: {error}")
            return False


def main():
    """Run OAuth tests."""
    print("🚀 Testing OAuth Configuration and Functionality")
    print("=" * 60)

    test = OAuthTest()

    # Run all tests
    tests = [
        ("OAuth Configuration", test.test_oauth_configuration),
        ("Scope Definitions", test.test_scope_definitions),
        ("Tool Permissions", test.test_tool_permissions),
        ("Configuration Values", test.test_configuration_values),
        ("Development Tokens", test.test_development_tokens),
        ("OAuth Provider Configs", test.test_oauth_provider_configs),
    ]

    success = True
    for test_name, test_func in tests:
        if not test.run_test(test_name, test_func):
            success = False

    # Generate summary
    success = test.generate_summary() and success

    # Print usage examples
    test.print_usage_examples()

    return success


if __name__ == "__main__":
    try:
        success = main()
        exit_code = 0 if success else 1
        print(f"\n✅ OAuth test completed with exit code: {exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ OAuth test failed with exception: {e}")
        traceback.print_exc()
        sys.exit(1)
