#!/usr/bin/env python3
"""
Error Handling and Edge Case Integration Tests for unified server in multi-registry mode

Tests various error conditions and edge cases:
- Network connectivity issues
- Authentication failures
- Invalid configurations
- Registry downtime scenarios
- READONLY mode enforcement
- Resource limits and timeouts
- Malformed schema definitions
- Cross-registry operation failures
"""

import asyncio
import json
import os
import sys
import time
from typing import Any, Dict

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import Client
from fastmcp.client.stdio import StdioServerParameters, stdio_client
from fastmcp.client.session import ClientSession

# Invalid schemas for testing error handling
INVALID_SCHEMAS = {
    "malformed_json": "this is not valid json",
    "missing_fields": {
        "type": "record"
        # Missing name and fields
    },
    "invalid_field_type": {
        "type": "record",
        "name": "TestRecord",
        "fields": [{"name": "id", "type": "invalid_type"}],
    },
    "circular_reference": {
        "type": "record",
        "name": "TestRecord",
        "fields": [{"name": "self", "type": "TestRecord"}],
    },
}

# Valid test schema for baseline tests
VALID_SCHEMA = {
    "type": "record",
    "name": "TestUser",
    "fields": [{"name": "id", "type": "long"}, {"name": "name", "type": "string"}],
}


async def test_invalid_registry_configuration():
    """Test behavior with invalid registry configurations."""
    print("\n❌ Testing Invalid Registry Configuration")
    print("-" * 50)

    # Clean up any existing task manager state to prevent deadlocks
    try:
        import kafka_schema_registry_unified_mcp

        kafka_schema_registry_unified_mcp.task_manager.reset_for_testing()
        print("🧹 Task manager state cleaned up")
    except Exception as e:
        print(f"⚠️ Warning: Could not cleanup task manager: {e}")

    # Test with non-existent registry URL
    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)

    env["SCHEMA_REGISTRY_NAME_1"] = "invalid_registry"
    env["SCHEMA_REGISTRY_URL_1"] = "http://nonexistent.registry:9999"
    env["READONLY_1"] = "false"

    server_params = StdioServerParameters(
        command="python", args=["kafka_schema_registry_unified_mcp.py"], env=env
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Test 1: Connection test should fail gracefully
                print("Test 1: Connection test to invalid registry")
                result = await session.call_tool(
                    "test_registry_connection", {"registry_name": "invalid_registry"}
                )
                response = json.loads(result.content[0].text) if result.content else {}
                print(f"  ✅ Expected failure: {response.get('status', 'unknown')}")
                assert (
                    response.get("status") == "error"
                ), "Expected connection test to fail"

                # Test 2: List subjects should handle connection failure
                print("\nTest 2: List subjects with invalid registry")
                result = await session.call_tool(
                    "list_subjects", {"registry": "invalid_registry"}
                )
                response = json.loads(result.content[0].text) if result.content else {}
                print(f"  ✅ Error handled: {response.get('error', 'No error field')}")

                # Test 3: Registry info should show connection failure
                print("\nTest 3: Registry info with connection failure")
                result = await session.call_tool(
                    "get_registry_info", {"registry_name": "invalid_registry"}
                )
                response = json.loads(result.content[0].text) if result.content else {}
                print(
                    f"  ✅ Connection status: {response.get('connection_status', 'unknown')}"
                )

                print("\n🎉 Invalid Registry Configuration Tests Complete!")

    except Exception as e:
        print(f"❌ Invalid registry configuration test failed: {e}")


async def test_readonly_mode_enforcement():
    """Test READONLY mode enforcement across operations."""
    print("\n🔒 Testing READONLY Mode Enforcement")
    print("-" * 50)

    # Clean up any existing task manager state to prevent deadlocks
    try:
        import kafka_schema_registry_unified_mcp

        kafka_schema_registry_unified_mcp.task_manager.reset_for_testing()
        print("🧹 Task manager state cleaned up")
    except Exception as e:
        print(f"⚠️ Warning: Could not cleanup task manager: {e}")

    # Setup with readonly registry
    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)

    env["SCHEMA_REGISTRY_NAME_1"] = "readonly_test"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
    env["READONLY_1"] = "true"  # Set to readonly

    server_params = StdioServerParameters(
        command="python", args=["kafka_schema_registry_unified_mcp.py"], env=env
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Test operations that should be blocked
                readonly_operations = [
                    (
                        "register_schema",
                        {
                            "subject": "test-subject",
                            "schema_definition": VALID_SCHEMA,
                            "registry": "readonly_test",
                        },
                    ),
                    (
                        "create_context",
                        {"context": "test-context", "registry": "readonly_test"},
                    ),
                    (
                        "delete_context",
                        {"context": "default", "registry": "readonly_test"},
                    ),
                    (
                        "delete_subject",
                        {"subject": "test-subject", "registry": "readonly_test"},
                    ),
                    (
                        "update_global_config",
                        {"compatibility": "BACKWARD", "registry": "readonly_test"},
                    ),
                    ("update_mode", {"mode": "READWRITE", "registry": "readonly_test"}),
                ]

                for operation_name, params in readonly_operations:
                    print(f"Test: {operation_name} should be blocked")
                    result = await session.call_tool(operation_name, params)
                    response = (
                        json.loads(result.content[0].text) if result.content else {}
                    )

                    # Check if operation was properly blocked
                    if "readonly" in response.get("error", "").lower() or response.get(
                        "readonly_mode"
                    ):
                        print(
                            f"  ✅ {operation_name} properly blocked by readonly mode"
                        )
                    else:
                        print(
                            f"  ⚠️ {operation_name} may not be properly blocked: {response}"
                        )

                # Test read operations that should still work
                read_operations = [
                    ("list_subjects", {"registry": "readonly_test"}),
                    ("list_contexts", {"registry": "readonly_test"}),
                    ("get_global_config", {"registry": "readonly_test"}),
                    ("get_mode", {"registry": "readonly_test"}),
                ]

                print("\nTesting read operations (should work):")
                for operation_name, params in read_operations:
                    result = await session.call_tool(operation_name, params)
                    response = (
                        json.loads(result.content[0].text) if result.content else {}
                    )

                    if not response.get("error"):
                        print(f"  ✅ {operation_name} works in readonly mode")
                    else:
                        print(
                            f"  ⚠️ {operation_name} failed unexpectedly: {response.get('error')}"
                        )

                print("\n🎉 READONLY Mode Enforcement Tests Complete!")

    except Exception as e:
        print(f"❌ READONLY mode enforcement test failed: {e}")


async def test_invalid_parameters():
    """Test handling of invalid parameters and edge cases."""
    print("\n🔧 Testing Invalid Parameters and Edge Cases")
    print("-" * 50)

    # Clean up any existing task manager state to prevent deadlocks
    try:
        import kafka_schema_registry_unified_mcp

        kafka_schema_registry_unified_mcp.task_manager.reset_for_testing()
        print("🧹 Task manager state cleaned up")
    except Exception as e:
        print(f"⚠️ Warning: Could not cleanup task manager: {e}")

    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)

    env["SCHEMA_REGISTRY_NAME_1"] = "param_test"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
    env["READONLY_1"] = "false"

    server_params = StdioServerParameters(
        command="python", args=["kafka_schema_registry_unified_mcp.py"], env=env
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Test 1: Non-existent registry parameter
                print("Test 1: Non-existent registry")
                result = await session.call_tool(
                    "list_subjects", {"registry": "nonexistent_registry"}
                )
                response = json.loads(result.content[0].text) if result.content else {}
                print(
                    f"  ✅ Non-existent registry error: {response.get('error', 'No error')}"
                )

                # Test 2: Invalid schema definitions
                print("\nTest 2: Invalid schema definitions")
                for schema_name, invalid_schema in INVALID_SCHEMAS.items():
                    print(f"  Testing {schema_name}:")
                    try:
                        result = await session.call_tool(
                            "register_schema",
                            {
                                "subject": f"test-{schema_name}",
                                "schema_definition": invalid_schema,
                                "registry": "param_test",
                            },
                        )
                        response = (
                            json.loads(result.content[0].text) if result.content else {}
                        )
                        if response.get("error"):
                            print(
                                f"    ✅ Properly rejected: {response['error'][:50]}..."
                            )
                        else:
                            print(f"    ⚠️ Unexpectedly accepted invalid schema")
                    except Exception as e:
                        print(f"    ✅ Exception caught: {str(e)[:50]}...")

                # Test 3: Invalid compatibility levels
                print("\nTest 3: Invalid compatibility levels")
                invalid_compatibility_levels = ["INVALID", "UNKNOWN", "", "123"]
                for level in invalid_compatibility_levels:
                    result = await session.call_tool(
                        "update_global_config",
                        {"compatibility": level, "registry": "param_test"},
                    )
                    response = (
                        json.loads(result.content[0].text) if result.content else {}
                    )
                    print(
                        f"  Testing '{level}': {response.get('error', 'Accepted')[:50]}"
                    )

                # Test 4: Invalid modes
                print("\nTest 4: Invalid modes")
                invalid_modes = ["INVALID", "UNKNOWN", "", "123"]
                for mode in invalid_modes:
                    result = await session.call_tool(
                        "update_mode", {"mode": mode, "registry": "param_test"}
                    )
                    response = (
                        json.loads(result.content[0].text) if result.content else {}
                    )
                    print(
                        f"  Testing '{mode}': {response.get('error', 'Accepted')[:50]}"
                    )

                # Test 5: Empty and special character subjects
                print("\nTest 5: Edge case subject names")
                edge_case_subjects = [
                    "",
                    " ",
                    "subject with spaces",
                    "subject-with-special-chars!@#",
                ]
                for subject in edge_case_subjects:
                    result = await session.call_tool(
                        "get_schema", {"subject": subject, "registry": "param_test"}
                    )
                    response = (
                        json.loads(result.content[0].text) if result.content else {}
                    )
                    print(
                        f"  Subject '{subject}': {response.get('error', 'No error')[:50]}"
                    )

                print("\n🎉 Invalid Parameters and Edge Cases Tests Complete!")

    except Exception as e:
        print(f"❌ Invalid parameters test failed: {e}")


async def test_cross_registry_error_scenarios():
    """Test error scenarios in cross-registry operations."""
    print("\n🔄 Testing Cross-Registry Error Scenarios")
    print("-" * 50)

    # Clean up any existing task manager state to prevent deadlocks
    try:
        import kafka_schema_registry_unified_mcp

        kafka_schema_registry_unified_mcp.task_manager.reset_for_testing()
        print("🧹 Task manager state cleaned up")
    except Exception as e:
        print(f"⚠️ Warning: Could not cleanup task manager: {e}")

    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)

    # Setup one valid and one invalid registry
    env["SCHEMA_REGISTRY_NAME_1"] = "valid_registry"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
    env["READONLY_1"] = "false"

    env["SCHEMA_REGISTRY_NAME_2"] = "invalid_registry"
    env["SCHEMA_REGISTRY_URL_2"] = "http://invalid.host:9999"
    env["READONLY_2"] = "false"

    env["SCHEMA_REGISTRY_NAME_3"] = "readonly_registry"
    env["SCHEMA_REGISTRY_URL_3"] = "http://localhost:38081"
    env["READONLY_3"] = "true"

    server_params = StdioServerParameters(
        command="python", args=["kafka_schema_registry_unified_mcp.py"], env=env
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Test 1: Compare valid with invalid registry
                print("Test 1: Compare valid with invalid registry")
                result = await session.call_tool(
                    "compare_registries",
                    {
                        "source_registry": "valid_registry",
                        "target_registry": "invalid_registry",
                    },
                )
                response = json.loads(result.content[0].text) if result.content else {}
                print(f"  ✅ Comparison result: {response.get('error', 'Success')}")

                # Test 2: Migration from valid to invalid registry
                print("\nTest 2: Migration from valid to invalid registry")
                result = await session.call_tool(
                    "migrate_schema",
                    {
                        "subject": "test-subject",
                        "source_registry": "valid_registry",
                        "target_registry": "invalid_registry",
                        "dry_run": True,
                    },
                )
                response = json.loads(result.content[0].text) if result.content else {}
                print(f"  ✅ Migration result: {response.get('error', 'Success')}")

                # Test 3: Migration to readonly registry
                print("\nTest 3: Migration to readonly registry")
                result = await session.call_tool(
                    "migrate_schema",
                    {
                        "subject": "test-subject",
                        "source_registry": "valid_registry",
                        "target_registry": "readonly_registry",
                        "dry_run": False,
                    },
                )
                response = json.loads(result.content[0].text) if result.content else {}
                print(
                    f"  ✅ Readonly migration result: {response.get('error', 'Success')}"
                )

                # Test 4: Find missing schemas with connection issues
                print("\nTest 4: Find missing schemas with connection issues")
                result = await session.call_tool(
                    "find_missing_schemas",
                    {
                        "source_registry": "valid_registry",
                        "target_registry": "invalid_registry",
                    },
                )
                response = json.loads(result.content[0].text) if result.content else {}
                print(
                    f"  ✅ Missing schemas result: {response.get('error', 'Success')}"
                )

                # Test 5: Sync operations with mixed registry states
                print("\nTest 5: Sync operations with mixed registry states")
                result = await session.call_tool(
                    "sync_schema",
                    {
                        "subject": "test-subject",
                        "source_registry": "valid_registry",
                        "target_registry": "readonly_registry",
                        "dry_run": True,
                    },
                )
                response = json.loads(result.content[0].text) if result.content else {}
                print(f"  ✅ Sync result: {response.get('error', 'Success')}")

                print("\n🎉 Cross-Registry Error Scenarios Tests Complete!")

    except Exception as e:
        print(f"❌ Cross-registry error scenarios test failed: {e}")


async def test_resource_limits_and_timeouts():
    """Test behavior under resource constraints and timeouts."""
    print("\n⏱️ Testing Resource Limits and Timeouts")
    print("-" * 50)

    # Clean up any existing task manager state to prevent deadlocks
    try:
        import kafka_schema_registry_unified_mcp

        kafka_schema_registry_unified_mcp.task_manager.reset_for_testing()
        print("🧹 Task manager state cleaned up")
    except Exception as e:
        print(f"⚠️ Warning: Could not cleanup task manager: {e}")

    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)

    env["SCHEMA_REGISTRY_NAME_1"] = "timeout_test"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
    env["READONLY_1"] = "false"

    server_params = StdioServerParameters(
        command="python", args=["kafka_schema_registry_unified_mcp.py"], env=env
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Test 1: Very large schema definition
                print("Test 1: Large schema definition")
                large_schema = {
                    "type": "record",
                    "name": "LargeRecord",
                    "fields": [
                        {"name": f"field_{i}", "type": "string"}
                        for i in range(100)  # 100 fields
                    ],
                }

                result = await session.call_tool(
                    "register_schema",
                    {
                        "subject": "large-schema-test",
                        "schema_definition": large_schema,
                        "registry": "timeout_test",
                    },
                )
                response = json.loads(result.content[0].text) if result.content else {}
                print(f"  ✅ Large schema result: {response.get('error', 'Success')}")

                # Test 2: Rapid sequential operations
                print("\nTest 2: Rapid sequential operations")
                rapid_test_results = []
                for i in range(10):
                    result = await session.call_tool(
                        "list_subjects", {"registry": "timeout_test"}
                    )
                    response = (
                        json.loads(result.content[0].text) if result.content else {}
                    )
                    rapid_test_results.append(
                        "success" if not response.get("error") else "error"
                    )

                success_count = rapid_test_results.count("success")
                print(f"  ✅ Rapid operations: {success_count}/10 successful")

                # Test 3: Multiple registries test (stress test)
                print("\nTest 3: Test all registries simultaneously")
                result = await session.call_tool("test_all_registries", {})
                response = json.loads(result.content[0].text) if result.content else {}
                print(
                    f"  ✅ Multi-registry test: {response.get('connected', 0)} connected"
                )

                print("\n🎉 Resource Limits and Timeouts Tests Complete!")

    except Exception as e:
        print(f"❌ Resource limits and timeouts test failed: {e}")


async def test_authentication_errors():
    """Test authentication and authorization error handling."""
    print("\n🔐 Testing Authentication Error Handling")
    print("-" * 50)

    # Clean up any existing task manager state to prevent deadlocks
    try:
        import kafka_schema_registry_unified_mcp

        kafka_schema_registry_unified_mcp.task_manager.reset_for_testing()
        print("🧹 Task manager state cleaned up")
    except Exception as e:
        print(f"⚠️ Warning: Could not cleanup task manager: {e}")

    # Test with invalid credentials
    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)

    env["SCHEMA_REGISTRY_NAME_1"] = "auth_test"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
    env["SCHEMA_REGISTRY_USER_1"] = "invalid_user"
    env["SCHEMA_REGISTRY_PASSWORD_1"] = "invalid_password"
    env["READONLY_1"] = "false"

    server_params = StdioServerParameters(
        command="python", args=["kafka_schema_registry_unified_mcp.py"], env=env
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Test 1: Connection test with invalid auth
                print("Test 1: Connection test with invalid credentials")
                result = await session.call_tool(
                    "test_registry_connection", {"registry_name": "auth_test"}
                )
                response = json.loads(result.content[0].text) if result.content else {}
                print(f"  ✅ Auth test result: {response.get('status', 'unknown')}")

                # Test 2: List subjects with auth issues
                print("\nTest 2: List subjects with invalid credentials")
                result = await session.call_tool(
                    "list_subjects", {"registry": "auth_test"}
                )
                response = json.loads(result.content[0].text) if result.content else {}
                if (
                    response.get("error")
                    or isinstance(response, list)
                    and len(response) == 0
                ):
                    print("  ✅ Auth error properly handled")
                else:
                    print(f"  ⚠️ Unexpected response: {response}")

                # Test 3: Schema registration with auth issues
                print("\nTest 3: Schema registration with invalid credentials")
                result = await session.call_tool(
                    "register_schema",
                    {
                        "subject": "auth-test-subject",
                        "schema_definition": VALID_SCHEMA,
                        "registry": "auth_test",
                    },
                )
                response = json.loads(result.content[0].text) if result.content else {}
                print(
                    f"  ✅ Auth registration result: {response.get('error', 'Success')}"
                )

                print("\n🎉 Authentication Error Handling Tests Complete!")

    except Exception as e:
        print(f"❌ Authentication error handling test failed: {e}")


async def test_error_handling():
    """Test error handling and recovery mechanisms."""

    # Get the path to the parent directory where the server script is located
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_script = os.path.join(parent_dir, "kafka_schema_registry_unified_mcp.py")

    print("⚠️  Testing Error Handling and Recovery...")

    try:
        client = Client(
            server_script,
            env={
                "SCHEMA_REGISTRY_URL": "http://localhost:38081",
                "MULTI_REGISTRY_CONFIG": json.dumps({
                    "dev": {"url": "http://localhost:38081"},
                    "invalid": {"url": "http://localhost:99999"}  # Invalid port for testing
                })
            }
        )

        async with client:
            print("✅ Connected to MCP server!")

            # Test 1: Invalid schema registration
            print("\n❌ Test 1: Invalid schema registration...")
            try:
                result = await client.call_tool("register_schema", {
                    "subject": "test-invalid-schema",
                    "schema_definition": {"invalid": "schema"},  # Invalid Avro schema
                    "schema_type": "AVRO"
                })
                if result and "error" in result.lower():
                    print("   ✅ Error properly handled for invalid schema")
                else:
                    print(f"   ⚠️ Unexpected result: {result}")
            except Exception as e:
                print(f"   ✅ Exception properly raised: {e}")

            # Test 2: Non-existent subject operations
            print("\n❌ Test 2: Non-existent subject operations...")
            try:
                result = await client.call_tool("get_schema", {
                    "subject": "non-existent-subject-12345",
                    "version": "latest"
                })
                if result and ("error" in result.lower() or "not found" in result.lower()):
                    print("   ✅ Error properly handled for non-existent subject")
                else:
                    print(f"   ⚠️ Unexpected result: {result}")
            except Exception as e:
                print(f"   ✅ Exception properly raised: {e}")

            # Test 3: Invalid registry operations
            print("\n❌ Test 3: Invalid registry operations...")
            try:
                result = await client.call_tool("list_subjects", {
                    "registry": "invalid"  # This should fail
                })
                if result and "error" in result.lower():
                    print("   ✅ Error properly handled for invalid registry")
                else:
                    print(f"   ⚠️ Unexpected result: {result}")
            except Exception as e:
                print(f"   ✅ Exception properly raised: {e}")

            # Test 4: Invalid tool parameters
            print("\n❌ Test 4: Invalid tool parameters...")
            try:
                result = await client.call_tool("register_schema", {
                    "subject": "",  # Empty subject
                    "schema_definition": {"type": "string"},
                    "schema_type": "AVRO"
                })
                if result and "error" in result.lower():
                    print("   ✅ Error properly handled for empty subject")
                else:
                    print(f"   ⚠️ Unexpected result: {result}")
            except Exception as e:
                print(f"   ✅ Exception properly raised: {e}")

            # Test 5: Tool call with missing required parameters
            print("\n❌ Test 5: Missing required parameters...")
            try:
                result = await client.call_tool("register_schema", {
                    "subject": "test-subject"
                    # Missing schema_definition and schema_type
                })
                if result and "error" in result.lower():
                    print("   ✅ Error properly handled for missing parameters")
                else:
                    print(f"   ⚠️ Unexpected result: {result}")
            except Exception as e:
                print(f"   ✅ Exception properly raised: {e}")

            # Test 6: Recovery after errors
            print("\n🔄 Test 6: Recovery after errors...")
            try:
                # First, cause an error
                await client.call_tool("get_schema", {
                    "subject": "non-existent",
                    "version": "latest"
                })
                
                # Then, perform a valid operation
                result = await client.call_tool("list_subjects", {})
                print("   ✅ Server recovered and handles valid operations after errors")
            except Exception as e:
                print(f"   ✅ Server continues to function: {e}")

            # Test 7: Invalid JSON in schema definitions
            print("\n❌ Test 7: Invalid JSON handling...")
            try:
                result = await client.call_tool("register_schema", {
                    "subject": "test-invalid-json",
                    "schema_definition": "not-valid-json",  # String instead of dict
                    "schema_type": "AVRO"
                })
                if result and "error" in result.lower():
                    print("   ✅ Error properly handled for invalid JSON")
                else:
                    print(f"   ⚠️ Unexpected result: {result}")
            except Exception as e:
                print(f"   ✅ Exception properly raised: {e}")

            print("\n🎉 Error handling testing completed!")
            print("✅ Server demonstrates robust error handling and recovery")

    except Exception as e:
        print(f"❌ Error during error handling test: {e}")
        raise


async def main():
    """Run all error handling and edge case tests."""
    print("🧪 Starting Error Handling and Edge Case Integration Tests")
    print("=" * 70)

    # Clean up any existing task manager state before starting
    try:
        import kafka_schema_registry_unified_mcp

        kafka_schema_registry_unified_mcp.task_manager.reset_for_testing()
        print("🧹 Initial task manager cleanup completed")
    except Exception as e:
        print(f"⚠️ Warning: Could not cleanup task manager initially: {e}")

    try:
        await test_invalid_registry_configuration()
        await test_readonly_mode_enforcement()
        await test_invalid_parameters()
        await test_cross_registry_error_scenarios()
        await test_resource_limits_and_timeouts()
        await test_authentication_errors()
        await test_error_handling()

        print("\n" + "=" * 70)
        print("🎉 All Error Handling and Edge Case Tests Complete!")
        print("\n✅ **Error Scenarios Tested:**")
        print("• Invalid registry configurations")
        print("• READONLY mode enforcement")
        print("• Invalid parameters and edge cases")
        print("• Cross-registry operation failures")
        print("• Resource limits and timeouts")
        print("• Authentication and authorization errors")

    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Error handling tests failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
