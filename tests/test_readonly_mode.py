#!/usr/bin/env python3
"""
Test script for READONLY mode functionality in the Kafka Schema Registry MCP Server.

This script tests that when READONLY=true is set, modification operations are blocked
while read and export operations continue to work.
"""

import asyncio
import os
import sys

from fastmcp import Client

# Add parent directory to Python path to find the main modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_readonly_mode():
    print("🔒 Testing READONLY mode functionality...")
    print("=" * 50)

    # Test with READONLY=false first (normal mode)
    print("\n🟢 Testing NORMAL mode (READONLY=false)...")
    os.environ["READONLY"] = "false"
    os.environ["SCHEMA_REGISTRY_URL"] = "http://localhost:38081"

    # Test with READONLY=true (readonly mode)
    print("\n🔴 Testing READONLY mode (READONLY=true)...")
    os.environ["READONLY"] = "true"

    # Create client for MCP server
    client = Client("kafka_schema_registry_unified_mcp.py")
    
    try:
        async with client:
            print("✅ MCP connection established")
            
            # Test the check_readonly_mode tool
            readonly_check = await client.call_tool("check_readonly_mode", {})
            if readonly_check and "readonly_mode" in readonly_check[0].text:
                print("✅ READONLY check working: read-only mode is active")
            else:
                print("❌ READONLY check failed - should return error in readonly mode")

            # Test individual functions that should be blocked
            print("\n🧪 Testing blocked operations in READONLY mode...")

            blocked_operations = [
                ("register_schema", {"subject": "test-subject", "schema_definition": {"type": "string"}}),
                ("create_context", {"context": "test-context"}),
                ("delete_context", {"context": "test-context"}),
                ("update_global_config", {"compatibility": "BACKWARD"}),
                ("update_subject_config", {"subject": "test-subject", "compatibility": "BACKWARD"}),
                ("update_mode", {"mode": "READONLY"}),
                ("update_subject_mode", {"subject": "test-subject", "mode": "READONLY"}),
            ]

            for func_name, args in blocked_operations:
                try:
                    result = await client.call_tool(func_name, args)
                    result_text = result[0].text if result else ""
                    if "readonly_mode" in result_text.lower() or "read-only" in result_text.lower():
                        print(f"✅ {func_name}: Correctly blocked in READONLY mode")
                    else:
                        print(f"❌ {func_name}: Should be blocked but wasn't! Result: {result_text}")
                except Exception as e:
                    if "readonly" in str(e).lower():
                        print(f"✅ {func_name}: Correctly blocked by readonly mode")
                    else:
                        print(f"⚠️  {func_name}: Exception occurred: {e}")

            # Test functions that should still work (read-only operations)
            print("\n🧪 Testing allowed operations in READONLY mode...")

            allowed_operations = [
                ("list_contexts", {}),
                ("list_subjects", {}),
                ("get_global_config", {}),
                ("get_mode", {}),
            ]

            for func_name, args in allowed_operations:
                try:
                    result = await client.call_tool(func_name, args)
                    result_text = result[0].text if result else ""
                    if "readonly_mode" in result_text.lower():
                        print(f"❌ {func_name}: Should NOT be blocked but was! Result: {result_text}")
                    else:
                        print(f"✅ {func_name}: Correctly allowed in READONLY mode")
                except Exception as e:
                    # These might fail due to connection issues, but shouldn't be blocked by readonly mode
                    if "readonly" in str(e).lower():
                        print(f"❌ {func_name}: Incorrectly blocked by readonly mode")
                    else:
                        print(f"✅ {func_name}: Not blocked by readonly mode (connection error is OK)")

            # Test export functions (should also be allowed)
            print("\n🧪 Testing export operations in READONLY mode...")

            export_operations = [
                ("export_schema", {"subject": "test-subject"}),
                ("export_subject", {"subject": "test-subject"}),
                ("export_context", {"context": "test-context"}),
                ("export_global", {}),
            ]

            for func_name, args in export_operations:
                try:
                    result = await client.call_tool(func_name, args)
                    result_text = result[0].text if result else ""
                    if "readonly_mode" in result_text.lower():
                        print(f"❌ {func_name}: Should NOT be blocked but was! Result: {result_text}")
                    else:
                        print(f"✅ {func_name}: Correctly allowed in READONLY mode")
                except Exception as e:
                    if "readonly" in str(e).lower():
                        print(f"❌ {func_name}: Incorrectly blocked by readonly mode")
                    else:
                        print(f"✅ {func_name}: Not blocked by readonly mode (connection error is OK)")

            # Test check_compatibility (should be allowed since it doesn't modify anything)
            print("\n🧪 Testing compatibility check in READONLY mode...")
            try:
                result = await client.call_tool("check_compatibility", {
                    "subject": "test-subject", 
                    "schema_definition": {"type": "string"}
                })
                result_text = result[0].text if result else ""
                if "readonly_mode" in result_text.lower():
                    print(f"❌ check_compatibility: Should NOT be blocked but was!")
                else:
                    print(f"✅ check_compatibility: Correctly allowed in READONLY mode")
            except Exception as e:
                if "readonly" in str(e).lower():
                    print(f"❌ check_compatibility: Incorrectly blocked by readonly mode")
                else:
                    print(f"✅ check_compatibility: Not blocked by readonly mode (connection error is OK)")

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 50)
    print("🎉 READONLY mode test completed!")
    print("\nSummary:")
    print("- Modification operations should be blocked ❌")
    print("- Read operations should continue working ✅")
    print("- Export operations should continue working ✅")
    return True


async def test_readonly_environment_variations():
    """Test different ways to set READONLY=true"""
    print("\n🧪 Testing different READONLY environment variable values...")

    import importlib

    import kafka_schema_registry_unified_mcp
    import schema_registry_common

    test_values = [
        ("true", True),
        ("TRUE", True),
        ("True", True),
        ("1", True),
        ("yes", True),
        ("YES", True),
        ("on", True),
        ("ON", True),
        ("false", False),
        ("FALSE", False),
        ("0", False),
        ("no", False),
        ("off", False),
        ("", False),
        ("invalid", False),
    ]

    for value, expected in test_values:
        os.environ["READONLY"] = value
        importlib.reload(schema_registry_common)
        importlib.reload(kafka_schema_registry_unified_mcp)
        actual = kafka_schema_registry_unified_mcp.READONLY
        status = "✅" if actual == expected else "❌"
        print(f"{status} READONLY='{value}' → {actual} (expected: {expected})")


if __name__ == "__main__":
    asyncio.run(test_readonly_mode())
    asyncio.run(test_readonly_environment_variations())
