#!/usr/bin/env python3
"""
PROD registry read-only enforcement

Tests that the MCP server correctly enforces read-only mode for the PROD registry
by blocking modification operations through MCP tools.
"""

import asyncio
import json
import os
import subprocess
import sys

# SET UP ENVIRONMENT VARIABLES FIRST - BEFORE ANY SERVER IMPORTS
# Clear any conflicting settings first
for var in ["READONLY", "SCHEMA_REGISTRY_URL", "SCHEMA_REGISTRY_NAME"]:
    if var in os.environ:
        del os.environ[var]

# Set up multi-registry environment variables BEFORE server imports
env_vars = {
    "SCHEMA_REGISTRY_NAME_1": "development",
    "SCHEMA_REGISTRY_URL_1": "http://localhost:38081",
    "READONLY_1": "false",
    "SCHEMA_REGISTRY_NAME_2": "production",
    "SCHEMA_REGISTRY_URL_2": "http://localhost:38082",
    "READONLY_2": "true",
    "ALLOW_LOCALHOST": "true",  # Allow localhost URLs in test mode
    "TESTING": "true"  # Mark as testing environment
}

# Apply environment variables before any imports
for key, value in env_vars.items():
    os.environ[key] = value

print(f"🔧 Setting up environment variables for readonly test...")
for key, value in env_vars.items():
    print(f"   {key}={value}")

# Add parent directory to Python path to find the main modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ReadOnlyValidationTest:
    """Test class for read-only validation scenarios"""

    def __init__(self):
        """Initialize test - environment already set at module level"""
        print(f"   Environment configured for multi-registry with readonly PROD")

    def parse_result(self, result):
        """Parse MCP tool result with simple error handling"""
        if not result:
            return {}
        
        try:
            # Handle FastMCP response format
            if isinstance(result, list) and len(result) > 0:
                text = result[0].text if hasattr(result[0], 'text') else str(result[0])
            else:
                text = str(result) if result else "{}"
            
            return json.loads(text)
        except json.JSONDecodeError:
            # If it's not JSON, return as-is
            return result if isinstance(result, (list, dict)) else {"response": str(result)}

    async def run_test(self):
        """Test unified server in multi-registry mode's read-only enforcement for PROD registry"""

        print(f"🧪 Starting MCP read-only validation test...")

        try:
            # Get the path to the parent directory where the server script is located
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            server_script = os.path.join(parent_dir, "kafka_schema_registry_unified_mcp.py")
            
            # Debug: Show environment variables that will be passed
            print(f"\n🔍 Debug: Environment variables for server:")
            for i in range(1, 3):
                name_var = f"SCHEMA_REGISTRY_NAME_{i}"
                url_var = f"SCHEMA_REGISTRY_URL_{i}"
                readonly_var = f"READONLY_{i}"
                print(f"   {name_var}={os.environ.get(name_var, 'NOT_SET')}")
                print(f"   {url_var}={os.environ.get(url_var, 'NOT_SET')}")
                print(f"   {readonly_var}={os.environ.get(readonly_var, 'NOT_SET')}")
            
            # Use subprocess to run server with proper environment
            print("\n🚀 Starting MCP server subprocess with environment...")
            
            # Import required modules for subprocess communication
            from mcp import ClientSession
            from mcp.client.stdio import stdio_client, StdioServerParameters
            
            # Create environment dict for subprocess
            subprocess_env = os.environ.copy()
            
            # Create server parameters with explicit environment
            server_params = StdioServerParameters(
                command="python", 
                args=[server_script], 
                env=subprocess_env
            )
            
            # Test with subprocess communication
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    print("✅ MCP server subprocess initialized with environment")

                    # Test 1: Verify registries are configured correctly
                    print("\n🔍 Testing registry configuration...")

                    result = await session.call_tool("list_registries", {})
                    if result.content and len(result.content) > 0:
                        registries = json.loads(result.content[0].text)
                    else:
                        registries = []
                    
                    print(f"   📋 Found registries: {registries}")
                    
                    if isinstance(registries, list):
                        registry_names = [r.get('name') for r in registries if isinstance(r, dict)]
                    else:
                        registry_names = []
                    
                    print(f"   📋 Configured registries: {registry_names}")

                    # Check that we have both registries
                    if "development" not in registry_names or "production" not in registry_names:
                        print(f"   ❌ Expected both 'development' and 'production' registries, got: {registry_names}")
                        return False

                    print("   ✅ Both DEV and PROD registries configured")

                    # Test 2: Test write operations on PROD registry (should be blocked)
                    print("\n🚫 Testing write operation blocking on PROD registry...")

                    test_schema = {
                        "type": "record",
                        "name": "ReadOnlyTestSchema",
                        "fields": [
                            {"name": "id", "type": "int"},
                            {"name": "message", "type": "string"},
                        ],
                    }

                    # Try to register schema in PROD (should be blocked by readonly mode)
                    result = await session.call_tool("register_schema", {
                        "subject": "readonly-test-value",
                        "schema_definition": test_schema,
                        "registry": "production"
                    })
                    
                    if result.content and len(result.content) > 0:
                        prod_result = json.loads(result.content[0].text)
                    else:
                        prod_result = {}

                    if isinstance(prod_result, dict) and prod_result.get("readonly_mode"):
                        print(f"   ✅ PROD write correctly blocked: {prod_result.get('error', 'Read-only mode')}")
                    else:
                        print(f"   ❌ PROD write NOT blocked by readonly mode! Result: {prod_result}")
                        return False

                    # Test 3: Test write operations on DEV registry (should work)
                    print("\n✏️  Testing write operations on DEV registry...")

                    # Try to register schema in DEV (should succeed or fail due to connection, not readonly)
                    result = await session.call_tool("register_schema", {
                        "subject": "readonly-test-value",
                        "schema_definition": test_schema,
                        "registry": "development"
                    })
                    
                    if result.content and len(result.content) > 0:
                        dev_result = json.loads(result.content[0].text)
                    else:
                        dev_result = {}

                    if isinstance(dev_result, dict) and dev_result.get("readonly_mode"):
                        print(f"   ❌ DEV incorrectly blocked by readonly mode: {dev_result}")
                        return False
                    else:
                        print(f"   ✅ DEV write operations: Not blocked by readonly mode")

                    # Test 4: Test other modification operations on PROD
                    print("\n🚫 Testing other modification operations on PROD...")

                    # Try to update global config (should be blocked)
                    result = await session.call_tool("update_global_config", {
                        "compatibility": "FULL",
                        "registry": "production"
                    })
                    
                    if result.content and len(result.content) > 0:
                        config_result = json.loads(result.content[0].text)
                    else:
                        config_result = {}

                    if isinstance(config_result, dict) and config_result.get("readonly_mode"):
                        print(f"   ✅ Config update correctly blocked")
                    else:
                        print(f"   ❌ Config update not blocked: {config_result}")

                    # Try to create context (should be blocked)
                    result = await session.call_tool("create_context", {
                        "context": "readonly-test-context",
                        "registry": "production"
                    })
                    
                    if result.content and len(result.content) > 0:
                        context_result = json.loads(result.content[0].text)
                    else:
                        context_result = {}

                    if isinstance(context_result, dict) and context_result.get("readonly_mode"):
                        print(f"   ✅ Context creation correctly blocked")
                    else:
                        print(f"   ❌ Context creation not blocked: {context_result}")

                    # Test 5: Test cross-registry operations
                    print("\n🔄 Testing cross-registry operations...")

                    # Migration to PROD should be blocked
                    result = await session.call_tool("migrate_schema", {
                        "subject": "readonly-test-value",
                        "source_registry": "development",
                        "target_registry": "production",
                        "dry_run": False
                    })
                    
                    if result.content and len(result.content) > 0:
                        migration_result = json.loads(result.content[0].text)
                    else:
                        migration_result = {}

                    if isinstance(migration_result, dict) and migration_result.get("readonly_mode"):
                        print(f"   ✅ Migration to PROD correctly blocked")
                    else:
                        print(f"   ⚠️  Migration response: {migration_result}")

                    print("\n✅ Read-only validation test completed successfully!")
                    return True

        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_readonly_validation():
    """Async wrapper for the test."""
    test_instance = ReadOnlyValidationTest()
    return await test_instance.run_test()


def run_readonly_validation():
    """Synchronous wrapper for the async test."""
    return asyncio.run(test_readonly_validation())


if __name__ == "__main__":
    success = run_readonly_validation()
    if not success:
        print("❌ Test failed")
        sys.exit(1)
    else:
        print("✅ Test passed")
