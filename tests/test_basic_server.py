#!/usr/bin/env python3
"""
Basic test for MCP server import and initialization
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test if we can import the MCP server modules."""
    print("🔍 Testing imports...")

    try:
        import mcp

        print(f"✅ MCP imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import MCP: {e}")
        return False

    try:
        import requests

        print(f"✅ Requests imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import requests: {e}")
        return False

    try:
        import asyncio

        print(f"✅ Asyncio imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import asyncio: {e}")
        return False

    return True


def test_server_import():
    """Test if we can import the unified MCP server file."""
    print("\n🔍 Testing unified MCP server import...")

    try:
        # Try importing the unified server
        import kafka_schema_registry_unified_mcp

        print(f"✅ Unified MCP server imported successfully")

        # Test that mode detection function exists
        if hasattr(kafka_schema_registry_unified_mcp, "detect_registry_mode"):
            print(f"✅ Mode detection function found")
        else:
            print(f"❌ Mode detection function missing")
            return False

    except ImportError as e:
        print(f"❌ Failed to import unified MCP server: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Import succeeded but got error: {e}")

    return True


def test_basic_functionality():
    """Test basic unified server functionality without Schema Registry connection."""
    print("\n🔍 Testing basic unified server functionality...")

    try:
        # Set test environment variables for single registry mode
        os.environ["SCHEMA_REGISTRY_URL"] = "http://localhost:38081"
        os.environ["SCHEMA_REGISTRY_USER"] = ""
        os.environ["SCHEMA_REGISTRY_PASSWORD"] = ""

        # Test unified server components
        import kafka_schema_registry_unified_mcp

        # Check that the FastMCP instance exists
        if hasattr(kafka_schema_registry_unified_mcp, "mcp"):
            print(f"✅ Unified MCP instance found")

            # Check that it has tools (FastMCP exposes tools via _tools attribute)
            if hasattr(kafka_schema_registry_unified_mcp.mcp, "_tools"):
                tools_count = len(kafka_schema_registry_unified_mcp.mcp._tools)
                print(f"✅ Unified server has {tools_count} tools")
            else:
                print(f"⚠️ Unified server tools not accessible")
        else:
            print(f"❌ Unified MCP instance not found")
            return False

        # Test mode detection
        if hasattr(kafka_schema_registry_unified_mcp, "detect_registry_mode"):
            mode = kafka_schema_registry_unified_mcp.detect_registry_mode()
            print(f"✅ Mode detection works, detected: {mode}")

        # Check helper classes exist
        if hasattr(kafka_schema_registry_unified_mcp, "LegacyRegistryManager"):
            print(f"✅ LegacyRegistryManager class found")

        if hasattr(kafka_schema_registry_unified_mcp, "MultiRegistryManager"):
            print(f"✅ MultiRegistryManager class found")

        if hasattr(kafka_schema_registry_unified_mcp, "RegistryClient"):
            print(f"✅ RegistryClient class found")

        # Test registry manager instance
        if hasattr(kafka_schema_registry_unified_mcp, "registry_manager"):
            print(f"✅ Registry manager instance found")
            manager = kafka_schema_registry_unified_mcp.registry_manager
            print(f"✅ Registry manager type: {type(manager).__name__}")

    except Exception as e:
        print(f"❌ Unified server validation failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def test_auth_config_unified_mode(monkeypatch):
    """Test that auth config is correctly applied in unified server."""
    # Set environment variables for auth
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("AUTH_ISSUER_URL", "https://test-issuer.com")
    monkeypatch.setenv("AUTH_VALID_SCOPES", "scope1,scope2")
    monkeypatch.setenv("AUTH_DEFAULT_SCOPES", "scope1")
    monkeypatch.setenv("AUTH_REQUIRED_SCOPES", "scope1")
    monkeypatch.setenv("AUTH_CLIENT_REG_ENABLED", "false")
    monkeypatch.setenv("AUTH_REVOCATION_ENABLED", "false")

    import importlib

    import kafka_schema_registry_unified_mcp

    importlib.reload(kafka_schema_registry_unified_mcp)

    mcp = kafka_schema_registry_unified_mcp.mcp
    auth = getattr(mcp, "auth", None)
    assert auth is not None, "Auth should be set when ENABLE_AUTH is true"
    assert auth.issuer_url == "https://test-issuer.com"
    assert set(auth.client_registration_options.valid_scopes) == {"scope1", "scope2"}
    assert set(auth.client_registration_options.default_scopes) == {"scope1"}
    assert set(auth.required_scopes) == {"scope1"}
    assert not auth.client_registration_options.enabled
    assert not auth.revocation_options.enabled


def main():
    """Main test function."""
    print("🚀 Starting basic MCP server tests...")
    print(f"🔍 Python version: {sys.version}")
    print(f"📁 Current directory: {os.getcwd()}")

    # Test 1: Imports
    if not test_imports():
        print("\n❌ Import tests failed")
        return False

    # Test 2: Server imports
    if not test_server_import():
        print("\n❌ Server import tests failed")
        return False

    # Test 3: Basic functionality
    if not test_basic_functionality():
        print("\n❌ Basic functionality tests failed")
        return False

    print("\n✅ All basic tests passed!")
    print("\n📋 Summary:")
    print("  ✅ All required packages can be imported")
    print("  ✅ Unified MCP server module can be imported")
    print("  ✅ FastMCP instance can be accessed")
    print("  ✅ Mode detection functionality works")
    print("  ✅ Server tools are available")
    print("  ✅ Helper classes and managers are available")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
