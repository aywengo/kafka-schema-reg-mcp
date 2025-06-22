#!/usr/bin/env python3
"""
Isolated test for OAuth provider configurations function.

This is a simple, focused test just for the get_oauth_provider_configs() function.
"""

import json
import os
import sys

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oauth_provider import get_oauth_provider_configs, get_oauth_scopes_info


def test_provider_configs():
    """Simple test for provider configurations."""
    print("🧪 Testing get_oauth_provider_configs()...")

    configs = get_oauth_provider_configs()

    # Basic structure test
    assert isinstance(configs, dict), "Should return a dictionary"

    # The function should return provider configurations for multiple providers
    expected_providers = ["azure", "google", "keycloak", "okta", "github"]

    for provider in expected_providers:
        assert provider in configs, f"Missing provider: {provider}"

        provider_config = configs[provider]
        assert isinstance(
            provider_config, dict
        ), f"Provider {provider} config should be a dict"

        # Check required keys for each provider
        required_keys = ["name", "issuer_url", "auth_url", "token_url", "scopes"]
        for key in required_keys:
            assert (
                key in provider_config
            ), f"Missing key '{key}' in provider '{provider}'"

        # Check that scopes is a list
        assert isinstance(
            provider_config["scopes"], list
        ), f"Scopes for {provider} should be a list"
        assert (
            len(provider_config["scopes"]) > 0
        ), f"Scopes for {provider} should not be empty"

    print("✅ Provider configuration structure test passed!")
    print(f"   Found {len(configs)} provider configurations")

    # Test OAuth status using get_oauth_scopes_info
    oauth_info = get_oauth_scopes_info()
    print(f"   OAuth enabled: {oauth_info.get('oauth_enabled', False)}")
    print(f"   Current provider: {oauth_info.get('provider', 'none')}")
    print(f"   Valid scopes: {oauth_info.get('valid_scopes', [])}")


def main():
    """Run the isolated test."""
    print("🚀 OAuth Provider Configs - Isolated Test")
    print("=" * 50)

    test_provider_configs()

    print("\n🎉 Test completed successfully!")
    print("\nProvider configurations available:")
    configs = get_oauth_provider_configs()
    for provider_name, config in configs.items():
        print(f"  • {provider_name}: {config.get('name', 'N/A')}")

    # Show current OAuth status
    oauth_info = get_oauth_scopes_info()
    print(f"\nCurrent OAuth Status:")
    print(f"  • Enabled: {oauth_info.get('oauth_enabled', False)}")
    print(f"  • Provider: {oauth_info.get('provider', 'none')}")
    print(f"  • Issuer: {oauth_info.get('issuer', 'none')}")
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
