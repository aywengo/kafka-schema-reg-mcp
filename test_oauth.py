#!/usr/bin/env python3
"""
OAuth Testing Script for Kafka Schema Registry MCP Server

This script demonstrates how to test OAuth functionality with development tokens.
It shows how different scopes provide different levels of access.
"""

import os
import json
from oauth_provider import get_oauth_scopes_info, ENABLE_AUTH

def print_separator(title):
    print("\n" + "="*50)
    print(f" {title} ")
    print("="*50)

def main():
    print_separator("OAuth Configuration Test")
    
    # Check if OAuth is enabled
    print(f"OAuth Enabled: {ENABLE_AUTH}")
    
    if not ENABLE_AUTH:
        print("\n❌ OAuth is disabled. Set ENABLE_AUTH=true to test OAuth functionality.")
        print("\nTo enable OAuth, run:")
        print("export ENABLE_AUTH=true")
        print("export AUTH_ISSUER_URL=https://your-auth-server.com")
        print("export AUTH_VALID_SCOPES=read,write,admin")
        print("export AUTH_DEFAULT_SCOPES=read")
        print("export AUTH_REQUIRED_SCOPES=read")
        return
    
    # Get OAuth configuration
    oauth_info = get_oauth_scopes_info()
    
    print_separator("Scope Definitions")
    for scope_name, scope_info in oauth_info["scope_definitions"].items():
        print(f"\n🔒 {scope_name.upper()} Scope (Level {scope_info['level']})")
        print(f"   Description: {scope_info['description']}")
        if 'requires' in scope_info:
            print(f"   Requires: {', '.join(scope_info['requires'])}")
        print(f"   Tools included: {', '.join(scope_info['includes'][:3])}...")
    
    print_separator("Test Tokens")
    if oauth_info["test_tokens"]:
        for token_name, token_value in oauth_info["test_tokens"].items():
            print(f"\n🎫 {token_name}: {token_value}")
    
    print_separator("Usage Examples")
    print("\nTo test with different permission levels:")
    print("\n1. READ-ONLY ACCESS:")
    print("   curl -H 'Authorization: Bearer dev-token-read' \\")
    print("        http://localhost:8000/subjects")
    
    print("\n2. READ-WRITE ACCESS:")
    print("   curl -H 'Authorization: Bearer dev-token-read,write' \\")
    print("        -X POST -d '{\"schema\": \"{...}\"}' \\")
    print("        http://localhost:8000/subjects/test-subject/versions")
    
    print("\n3. FULL ADMIN ACCESS:")
    print("   curl -H 'Authorization: Bearer dev-token-read,write,admin' \\")
    print("        -X DELETE \\")
    print("        http://localhost:8000/subjects/test-subject")
    
    print_separator("Environment Variables")
    oauth_vars = [
        "ENABLE_AUTH",
        "AUTH_ISSUER_URL", 
        "AUTH_VALID_SCOPES",
        "AUTH_DEFAULT_SCOPES",
        "AUTH_REQUIRED_SCOPES",
        "AUTH_CLIENT_REG_ENABLED",
        "AUTH_REVOCATION_ENABLED"
    ]
    
    for var in oauth_vars:
        value = os.getenv(var, "Not set")
        print(f"{var}: {value}")
    
    print_separator("Testing Tips")
    print("\n1. Start the MCP server:")
    print("   python kafka_schema_registry_multi_mcp.py")
    
    print("\n2. Test different scopes by changing the token:")
    print("   - dev-token-read (read-only)")
    print("   - dev-token-read,write (read + write)")
    print("   - dev-token-read,write,admin (full access)")
    
    print("\n3. Operations that should fail without proper scopes:")
    print("   - DELETE operations need 'admin' scope")
    print("   - POST/PUT operations need 'write' scope")
    print("   - GET operations need 'read' scope")
    
    print("\n4. Production setup:")
    print("   - Replace dev tokens with real JWT tokens")
    print("   - Implement proper token validation in oauth_provider.py")
    print("   - Set up a real OAuth 2.0 server (Auth0, Keycloak, etc.)")
    
    print("\n✅ OAuth test completed!")

if __name__ == "__main__":
    main() 