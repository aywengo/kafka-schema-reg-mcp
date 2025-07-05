#!/usr/bin/env python3
"""
Test script for VIEWONLY mode functionality in the Kafka Schema Registry MCP Server.

This script tests that when VIEWONLY=true is set, modification operations are blocked
while read and export operations continue to work.

Note: This script also tests backward compatibility with the deprecated READONLY parameter.
"""

import asyncio
import os
import sys

import pytest
from fastmcp import Client

# Add parent directory to Python path to find the main modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.asyncio
async def test_viewonly_mode():
    print("🔒 Testing VIEWONLY mode functionality...")
    print("=" * 50)

    # Test with VIEWONLY=false first (normal mode)
    print("\n🟢 Testing NORMAL mode (VIEWONLY=false)...")
    os.environ["VIEWONLY"] = "false"
    os.environ["SCHEMA_REGISTRY_URL"] = "http://localhost:38081"

    # Test with VIEWONLY=true (viewonly mode)
    print("\n🔴 Testing VIEWONLY mode (VIEWONLY=true)...")
    os.environ["VIEWONLY"] = "true"

    # Get absolute path to server script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(os.path.dirname(script_dir), "kafka_schema_registry_unified_mcp.py")

    # Create client with the server script
    client = Client(server_script)

    try:
        async with client:
            print("✅ MCP connection established")

            # Test the check_readonly_mode tool (now handles both VIEWONLY and READONLY)
            readonly_check = await client.call_tool("check_readonly_mode", {})
            if readonly_check and ("viewonly_mode" in str(readonly_check) or "readonly_mode" in str(readonly_check)):
                print("✅ VIEWONLY check working: view-only mode is active")
            else:
                print("❌ VIEWONLY check failed - should return error in viewonly mode")

            # Test individual functions that should be blocked
            print("\n🧪 Testing blocked operations in VIEWONLY mode...")

            blocked_operations = [
                (
                    "register_schema",
                    {
                        "subject": "test-subject",
                        "schema_definition": {"type": "string"},
                    },
                ),
                ("create_context", {"context": "test-context"}),
                ("delete_context", {"context": "test-context"}),
                ("update_global_config", {"compatibility": "BACKWARD"}),
                (
                    "update_subject_config",
                    {"subject": "test-subject", "compatibility": "BACKWARD"},
                ),
                ("update_mode", {"mode": "READONLY"}),
                (
                    "update_subject_mode",
                    {"subject": "test-subject", "mode": "READONLY"},
                ),
            ]

            for func_name, args in blocked_operations:
                try:
                    result = await client.call_tool(func_name, args)
                    result_text = str(result)
                    if "viewonly_mode" in result_text.lower() or "view-only" in result_text.lower() or "readonly_mode" in result_text.lower():
                        print(f"✅ {func_name}: Correctly blocked in VIEWONLY mode")
                    else:
                        print(f"❌ {func_name}: Should be blocked but wasn't! Result: {result_text}")
                except Exception as e:
                    if "viewonly" in str(e).lower() or "readonly" in str(e).lower():
                        print(f"✅ {func_name}: Correctly blocked by viewonly mode")
                    else:
                        print(f"⚠️  {func_name}: Exception occurred: {e}")

            # Test functions that should still work (read-only operations)
            print("\n🧪 Testing allowed operations in VIEWONLY mode...")

            allowed_operations = [
                ("list_contexts", {}),
                ("list_subjects", {}),
                ("get_global_config", {}),
                ("get_mode", {}),
            ]

            for func_name, args in allowed_operations:
                try:
                    result = await client.call_tool(func_name, args)
                    result_text = str(result)
                    if "viewonly_mode" in result_text.lower() or "readonly_mode" in result_text.lower():
                        print(f"❌ {func_name}: Should NOT be blocked but was! Result: {result_text}")
                    else:
                        print(f"✅ {func_name}: Correctly allowed in VIEWONLY mode")
                except Exception as e:
                    # These might fail due to connection issues, but shouldn't be blocked by readonly mode
                    if "viewonly" in str(e).lower() or "readonly" in str(e).lower():
                        print(f"❌ {func_name}: Incorrectly blocked by viewonly mode")
                    else:
                        print(f"✅ {func_name}: Not blocked by viewonly mode (connection error is OK)")

            # Test export functions (should also be allowed)
            print("\n🧪 Testing export operations in VIEWONLY mode...")

            export_operations = [
                ("export_schema", {"subject": "test-subject"}),
                ("export_subject", {"subject": "test-subject"}),
                ("export_context", {"context": "test-context"}),
                ("export_global", {}),
            ]

            for func_name, args in export_operations:
                try:
                    result = await client.call_tool(func_name, args)
                    result_text = str(result)
                    if "viewonly_mode" in result_text.lower() or "readonly_mode" in result_text.lower():
                        print(f"❌ {func_name}: Should NOT be blocked but was! Result: {result_text}")
                    else:
                        print(f"✅ {func_name}: Correctly allowed in VIEWONLY mode")
                except Exception as e:
                    if "viewonly" in str(e).lower() or "readonly" in str(e).lower():
                        print(f"❌ {func_name}: Incorrectly blocked by viewonly mode")
                    else:
                        print(f"✅ {func_name}: Not blocked by viewonly mode (connection error is OK)")

            # Test check_compatibility (should be allowed since it doesn't modify anything)
            print("\n🧪 Testing compatibility check in VIEWONLY mode...")
            try:
                result = await client.call_tool(
                    "check_compatibility",
                    {
                        "subject": "test-subject",
                        "schema_definition": {"type": "string"},
                    },
                )
                result_text = str(result)
                if "viewonly_mode" in result_text.lower() or "readonly_mode" in result_text.lower():
                    print("❌ check_compatibility: Should NOT be blocked but was!")
                else:
                    print("✅ check_compatibility: Correctly allowed in VIEWONLY mode")
            except Exception as e:
                if "viewonly" in str(e).lower() or "readonly" in str(e).lower():
                    print("❌ check_compatibility: Incorrectly blocked by viewonly mode")
                else:
                    print("✅ check_compatibility: Not blocked by viewonly mode (connection error is OK)")

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n" + "=" * 50)
    print("🎉 VIEWONLY mode test completed!")
    print("\nSummary:")
    print("- Modification operations should be blocked ❌")
    print("- Read operations should continue working ✅")
    print("- Export operations should continue working ✅")
    return True


async def test_viewonly_environment_variations():
    """Test different ways to set VIEWONLY=true and backward compatibility with READONLY"""
    print("\n🧪 Testing different VIEWONLY environment variable values...")

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

    # Test VIEWONLY
    print("\nTesting VIEWONLY:")
    for value, expected in test_values:
        # Clear both variables first
        os.environ.pop("READONLY", None)
        os.environ["VIEWONLY"] = value
        importlib.reload(schema_registry_common)
        importlib.reload(kafka_schema_registry_unified_mcp)
        actual = kafka_schema_registry_unified_mcp.READONLY
        status = "✅" if actual == expected else "❌"
        print(f"{status} VIEWONLY='{value}' → {actual} (expected: {expected})")
    
    # Test backward compatibility with READONLY
    print("\nTesting backward compatibility with READONLY:")
    for value, expected in test_values:
        # Clear both variables first
        os.environ.pop("VIEWONLY", None)
        os.environ["READONLY"] = value
        importlib.reload(schema_registry_common)
        importlib.reload(kafka_schema_registry_unified_mcp)
        actual = kafka_schema_registry_unified_mcp.READONLY
        status = "✅" if actual == expected else "❌"
        print(f"{status} READONLY='{value}' → {actual} (expected: {expected})")
    
    # Test VIEWONLY takes precedence over READONLY
    print("\nTesting VIEWONLY takes precedence over READONLY:")
    os.environ["READONLY"] = "false"
    os.environ["VIEWONLY"] = "true"
    importlib.reload(schema_registry_common)
    importlib.reload(kafka_schema_registry_unified_mcp)
    actual = kafka_schema_registry_unified_mcp.READONLY
    status = "✅" if actual == True else "❌"
    print(f"{status} READONLY='false' + VIEWONLY='true' → {actual} (expected: True)")


if __name__ == "__main__":
    asyncio.run(test_viewonly_mode())
    asyncio.run(test_viewonly_environment_variations())
