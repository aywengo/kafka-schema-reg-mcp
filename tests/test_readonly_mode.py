#!/usr/bin/env python3
"""
Test script for READONLY mode functionality in the Kafka Schema Registry MCP Server.

This script tests that when READONLY=true is set, modification operations are blocked
while read and export operations continue to work.
"""

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Add parent directory to Python path to find the main modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_readonly_mode():
    print("🔒 Testing READONLY mode functionality...")
    print("=" * 50)

    # Test with READONLY=false first (normal mode)
    print("\n🟢 Testing NORMAL mode (READONLY=false)...")
    os.environ["READONLY"] = "false"

    # Import the MCP server after setting environment
    import importlib

    import kafka_schema_registry_unified_mcp
    import schema_registry_common

    importlib.reload(schema_registry_common)
    importlib.reload(kafka_schema_registry_unified_mcp)

    print(f"READONLY setting: {kafka_schema_registry_unified_mcp.READONLY}")

    # Test with READONLY=true (readonly mode)
    print("\n🔴 Testing READONLY mode (READONLY=true)...")
    os.environ["READONLY"] = "true"

    # Reload the modules to pick up new environment variable
    importlib.reload(schema_registry_common)
    importlib.reload(kafka_schema_registry_unified_mcp)

    print(f"READONLY setting: {kafka_schema_registry_unified_mcp.READONLY}")

    # Test the helper function directly
    readonly_check = kafka_schema_registry_unified_mcp.check_readonly_mode()
    if readonly_check:
        print("✅ READONLY check working:", readonly_check)
    else:
        print("❌ READONLY check failed - should return error in readonly mode")

    # Test individual functions that should be blocked
    print("\n🧪 Testing blocked operations in READONLY mode...")

    blocked_functions = [
        (
            "register_schema",
            lambda: kafka_schema_registry_unified_mcp.register_schema(
                "test-subject", {"type": "string"}
            ),
        ),
        (
            "create_context",
            lambda: kafka_schema_registry_unified_mcp.create_context("test-context"),
        ),
        (
            "delete_context",
            lambda: kafka_schema_registry_unified_mcp.delete_context("test-context"),
        ),
        (
            "delete_subject",
            lambda: asyncio.run(kafka_schema_registry_unified_mcp.delete_subject("test-subject")),
        ),
        (
            "update_global_config",
            lambda: kafka_schema_registry_unified_mcp.update_global_config("BACKWARD"),
        ),
        (
            "update_subject_config",
            lambda: kafka_schema_registry_unified_mcp.update_subject_config(
                "test-subject", "BACKWARD"
            ),
        ),
        ("update_mode", lambda: kafka_schema_registry_unified_mcp.update_mode("READONLY")),
        (
            "update_subject_mode",
            lambda: kafka_schema_registry_unified_mcp.update_subject_mode(
                "test-subject", "READONLY"
            ),
        ),
    ]

    for func_name, func in blocked_functions:
        try:
            result = func()
            if isinstance(result, dict) and "readonly_mode" in result:
                print(f"✅ {func_name}: Correctly blocked in READONLY mode")
            else:
                print(f"❌ {func_name}: Should be blocked but wasn't! Result: {result}")
        except Exception as e:
            print(f"⚠️  {func_name}: Exception occurred: {e}")

    # Test functions that should still work (read-only operations)
    print("\n🧪 Testing allowed operations in READONLY mode...")

    allowed_functions = [
        ("list_contexts", lambda: kafka_schema_registry_unified_mcp.list_contexts()),
        ("list_subjects", lambda: kafka_schema_registry_unified_mcp.list_subjects()),
        ("get_global_config", lambda: kafka_schema_registry_unified_mcp.get_global_config()),
        ("get_mode", lambda: kafka_schema_registry_unified_mcp.get_mode()),
    ]

    for func_name, func in allowed_functions:
        try:
            result = func()
            if isinstance(result, dict) and "readonly_mode" in result:
                print(f"❌ {func_name}: Should NOT be blocked but was! Result: {result}")
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

    export_functions = [
        ("export_schema", lambda: kafka_schema_registry_unified_mcp.export_schema("test-subject")),
        (
            "export_subject",
            lambda: kafka_schema_registry_unified_mcp.export_subject("test-subject"),
        ),
        (
            "export_context",
            lambda: kafka_schema_registry_unified_mcp.export_context("test-context"),
        ),
        ("export_global", lambda: kafka_schema_registry_unified_mcp.export_global()),
    ]

    for func_name, func in export_functions:
        try:
            result = func()
            if isinstance(result, dict) and "readonly_mode" in result:
                print(f"❌ {func_name}: Should NOT be blocked but was! Result: {result}")
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
        result = kafka_schema_registry_unified_mcp.check_compatibility(
            "test-subject", {"type": "string"}
        )
        if isinstance(result, dict) and "readonly_mode" in result:
            print(f"❌ check_compatibility: Should NOT be blocked but was!")
        else:
            print(f"✅ check_compatibility: Correctly allowed in READONLY mode")
    except Exception as e:
        if "readonly" in str(e).lower():
            print(f"❌ check_compatibility: Incorrectly blocked by readonly mode")
        else:
            print(f"✅ check_compatibility: Not blocked by readonly mode (connection error is OK)")

    print("\n" + "=" * 50)
    print("🎉 READONLY mode test completed!")
    print("\nSummary:")
    print("- Modification operations should be blocked ❌")
    print("- Read operations should be allowed ✅")
    print("- Export operations should be allowed ✅")
    print("- Compatibility checks should be allowed ✅")


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
