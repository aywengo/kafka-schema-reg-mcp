#!/usr/bin/env python3
"""
Isolated test for OAuth provider configurations function.

This is a simple, focused test just for the get_oauth_provider_configs() function.
"""

import os
import sys
import json

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oauth_provider import get_oauth_provider_configs

def test_provider_configs():
    """Simple test for provider configurations."""
    print("🧪 Testing get_oauth_provider_configs()...")
    
    try:
        configs = get_oauth_provider_configs()
        
        # Basic structure test
        assert isinstance(configs, dict), "Should return a dictionary"
        assert len(configs) == 5, f"Should have 5 providers, got {len(configs)}"
        
        # Check all expected providers exist
        expected_providers = ["azure", "google", "keycloak", "okta", "github"]
        for provider in expected_providers:
            assert provider in configs, f"Missing provider: {provider}"
        
        # Test Azure config
        azure = configs["azure"]
        assert azure["name"] == "Azure AD / Entra ID"
        assert "tenant-id" in azure["issuer_url"]
        assert "https://graph.microsoft.com/User.Read" in azure["scopes"]
        
        # Test Google config
        google = configs["google"]
        assert google["name"] == "Google OAuth 2.0"
        assert google["issuer_url"] == "https://accounts.google.com"
        
        # Test Keycloak config
        keycloak = configs["keycloak"]
        assert keycloak["name"] == "Keycloak"
        assert "{keycloak-server}" in keycloak["issuer_url"]
        assert "{realm}" in keycloak["issuer_url"]
        
        # Test Okta config
        okta = configs["okta"]
        assert okta["name"] == "Okta"
        assert "{okta-domain}" in okta["issuer_url"]
        
        # Test GitHub config
        github = configs["github"]
        assert github["name"] == "GitHub OAuth"
        assert github["issuer_url"] == "https://api.github.com"
        assert github["auth_url"] == "https://github.com/login/oauth/authorize"
        assert github["token_url"] == "https://github.com/login/oauth/access_token"
        assert "read:user" in github["scopes"]
        assert "user:email" in github["scopes"]
        assert "read:org" in github["scopes"]
        
        # Test that all providers have required keys
        required_keys = ["name", "issuer_url", "auth_url", "token_url", "scopes", "setup_docs"]
        for provider_name, provider_config in configs.items():
            for key in required_keys:
                assert key in provider_config, f"Provider {provider_name} missing key: {key}"
        
        print("✅ All provider configuration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Run the isolated test."""
    print("🚀 OAuth Provider Configs - Isolated Test")
    print("=" * 50)
    
    success = test_provider_configs()
    
    if success:
        print("\n🎉 Test completed successfully!")
        print("\nProvider configurations:")
        configs = get_oauth_provider_configs()
        for provider, config in configs.items():
            print(f"  • {config['name']} ({provider})")
        return 0
    else:
        print("\n❌ Test failed!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 