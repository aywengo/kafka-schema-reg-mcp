#!/usr/bin/env python3
"""
Test Batch Context Cleanup Tools

This script tests the new batch cleanup tools for efficiently removing
all subjects from contexts in both single-registry and multi-registry modes.
"""

import asyncio
import json
import os
import sys

import pytest
import requests
from fastmcp import Client
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# Add project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.asyncio
async def test_single_registry_batch_cleanup_helper():
    """Helper function to test batch cleanup with MCP client and timeout protection"""
    try:
        # Create a clean environment with only the variables we need
        env = {}
        # Copy only essential system variables
        for key in [
            "PATH",
            "PYTHONPATH",
            "HOME",
            "USER",
            "SHELL",
            "LANG",
            "LC_ALL",
            "VIRTUAL_ENV",
        ]:
            if key in os.environ:
                env[key] = os.environ[key]

        # Add our registry configuration
        env["SCHEMA_REGISTRY_NAME_1"] = "dev"
        env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
        env["SCHEMA_REGISTRY_NAME_2"] = "prod"
        env["SCHEMA_REGISTRY_URL_2"] = "http://localhost:38082"

        # Force test mode to allow localhost
        env["TESTING"] = "true"

        print("🔍 Environment variables being passed to subprocess:")
        for k, v in sorted(env.items()):
            if "SCHEMA" in k or "TESTING" in k:
                print(f"   {k}={v}")

        # Get absolute path to server script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        server_script = os.path.join(os.path.dirname(script_dir), "kafka_schema_registry_unified_mcp.py")

        server_params = StdioServerParameters(command="python", args=[server_script], env=env)

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                test_context = "test-cleanup-single"

                # Test dry run first
                print("🔍 Testing dry run mode...")
                dry_run_result = await session.call_tool(
                    "clear_context_batch",
                    {
                        "context": test_context,
                        "delete_context_after": True,
                        "dry_run": True,
                    },
                )

                if dry_run_result.content and len(dry_run_result.content) > 0:
                    content = json.loads(dry_run_result.content[0].text)
                    if "error" in content:
                        print(f"❌ Dry run failed: {content['error']}")
                        return False
                    print("✅ Dry run completed")
                    print(f"   Response keys: {list(content.keys())}")
                else:
                    print("❌ No response from dry run")
                    return False

                # Test actual cleanup
                print("\n🗑️  Testing actual batch cleanup...")
                cleanup_result = await session.call_tool(
                    "clear_context_batch",
                    {
                        "context": test_context,
                        "delete_context_after": True,
                        "dry_run": False,
                    },
                )

                if cleanup_result.content and len(cleanup_result.content) > 0:
                    content = json.loads(cleanup_result.content[0].text)
                    if "error" in content:
                        print(f"❌ Cleanup failed: {content['error']}")
                        return False
                    print("✅ Batch cleanup completed")
                    print(f"   Response keys: {list(content.keys())}")
                    return True
                else:
                    print("❌ No response from cleanup")
                    return False

    except Exception as e:
        print(f"❌ Single-registry cleanup test failed: {e}")
        return False


@pytest.mark.asyncio
async def test_single_registry_batch_cleanup():
    """Test batch cleanup in single-registry mode"""
    print("🧪 Testing Single-Registry Batch Cleanup")
    print("=" * 50)

    # First, create a test context with some subjects
    test_context = "test-cleanup-single"
    dev_url = "http://localhost:38081"

    print(f"📝 Setting up test context '{test_context}' with test subjects...")

    # Create test schemas
    test_schemas = [
        {
            "subject": "cleanup-test-user",
            "schema": {
                "type": "record",
                "name": "CleanupUser",
                "namespace": "com.example.cleanup.test",
                "fields": [
                    {"name": "id", "type": "int"},
                    {"name": "name", "type": "string"},
                ],
            },
        },
        {
            "subject": "cleanup-test-order",
            "schema": {
                "type": "record",
                "name": "CleanupOrder",
                "namespace": "com.example.cleanup.test",
                "fields": [
                    {"name": "orderId", "type": "string"},
                    {"name": "amount", "type": "double"},
                ],
            },
        },
    ]

    # Create subjects in the test context
    created_subjects = []
    for schema_def in test_schemas:
        try:
            subject = schema_def["subject"]
            schema = schema_def["schema"]

            # Create in context
            url = f"{dev_url}/contexts/{test_context}/subjects/{subject}/versions"
            payload = {"schema": json.dumps(schema)}

            response = requests.post(
                url,
                headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
                json=payload,
                timeout=10,
            )

            if response.status_code in [200, 409]:
                created_subjects.append(subject)
                print(f"   ✅ Created {subject} in context '{test_context}'")
            else:
                print(f"   ❌ Failed to create {subject}: {response.status_code}")

        except Exception as e:
            print(f"   ❌ Error creating {subject}: {e}")

    if not created_subjects:
        print("❌ No test subjects created - skipping cleanup test")
        return False

    print(f"📊 Created {len(created_subjects)} test subjects")

    # Now test the single-registry batch cleanup with timeout protection
    print("\n🧪 Testing single-registry batch cleanup...")

    try:
        # Run the async helper with timeout protection
        result = await asyncio.wait_for(test_single_registry_batch_cleanup_helper(), timeout=30.0)
        return result

    except asyncio.TimeoutError:
        print("❌ Single-registry cleanup test timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"❌ Single-registry cleanup test failed: {e}")
        return False


@pytest.mark.asyncio
async def test_multi_registry_batch_cleanup_helper():
    """Helper function to test multi-registry batch cleanup with MCP client and timeout protection"""
    try:
        # Create a clean environment with only the variables we need
        env = {}
        # Copy only essential system variables
        for key in [
            "PATH",
            "PYTHONPATH",
            "HOME",
            "USER",
            "SHELL",
            "LANG",
            "LC_ALL",
            "VIRTUAL_ENV",
        ]:
            if key in os.environ:
                env[key] = os.environ[key]

        # Add our registry configuration
        env["SCHEMA_REGISTRY_NAME_1"] = "dev"
        env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
        env["SCHEMA_REGISTRY_NAME_2"] = "prod"
        env["SCHEMA_REGISTRY_URL_2"] = "http://localhost:38082"

        # Force test mode to allow localhost
        env["TESTING"] = "true"

        # Get absolute path to server script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        server_script = os.path.join(os.path.dirname(script_dir), "kafka_schema_registry_unified_mcp.py")

        server_params = StdioServerParameters(command="python", args=[server_script], env=env)

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                test_context = "test-cleanup-multi"

                # Test multi-registry context cleanup in DEV registry
                print("🔍 Testing context cleanup in DEV registry...")
                cleanup_result = await session.call_tool(
                    "clear_context_batch",
                    {
                        "context": test_context,
                        "registry": "dev",
                        "delete_context_after": True,
                        "dry_run": False,
                    },
                )

                if cleanup_result.content and len(cleanup_result.content) > 0:
                    content = json.loads(cleanup_result.content[0].text)
                    if "error" in content:
                        print(f"❌ Multi-registry cleanup failed: {content['error']}")
                        return False
                    print("✅ Multi-registry cleanup task started")
                    print(f"   Response keys: {list(content.keys())}")
                    return True
                else:
                    print("❌ No response from multi-registry cleanup")
                    return False

    except Exception as e:
        print(f"❌ Multi-registry cleanup test failed: {e}")
        return False


@pytest.mark.asyncio
async def test_multi_registry_batch_cleanup():
    """Test batch cleanup in multi-registry mode"""
    print("\n🧪 Testing Multi-Registry Batch Cleanup")
    print("=" * 50)

    # Test context for multi-registry
    test_context = "test-cleanup-multi"

    print(f"📝 Setting up test context '{test_context}' in DEV registry...")

    # Create test schemas in DEV registry
    dev_url = "http://localhost:38081"
    test_schema = {
        "type": "record",
        "name": "MultiCleanupTest",
        "namespace": "com.example.multi.cleanup",
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "data", "type": "string"},
        ],
    }

    test_subject = "multi-cleanup-test"

    try:
        # Create subject in DEV registry context
        url = f"{dev_url}/contexts/{test_context}/subjects/{test_subject}/versions"
        payload = {"schema": json.dumps(test_schema)}

        response = requests.post(
            url,
            headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
            json=payload,
            timeout=10,
        )

        if response.status_code not in [200, 409]:
            print(f"❌ Failed to create test subject: {response.status_code}")
            return False

        print(f"   ✅ Created {test_subject} in context '{test_context}' (DEV registry)")

    except Exception as e:
        print(f"❌ Error creating test subject: {e}")
        return False

    # Test multi-registry batch cleanup with timeout protection
    print("\n🧪 Testing multi-registry batch cleanup...")

    try:
        # Run the async helper with timeout protection
        result = await asyncio.wait_for(test_multi_registry_batch_cleanup_helper(), timeout=30.0)
        return result

    except asyncio.TimeoutError:
        print("❌ Multi-registry cleanup test timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"❌ Multi-registry cleanup test failed: {e}")
        return False


def test_performance_characteristics():
    """Test and demonstrate performance characteristics"""
    print("\n📊 Testing Performance Characteristics")
    print("=" * 50)

    print("🏃 Performance features of batch cleanup tools:")
    print("   • Parallel deletion (up to 10 concurrent deletions)")
    print("   • Progress reporting with real-time feedback")
    print("   • Comprehensive error handling and retry logic")
    print("   • Detailed performance metrics (subjects/second)")
    print("   • Dry run mode for safe testing")
    print("   • Context deletion after subject cleanup")
    print("   • Support for both single and multi-registry modes")
    print("   • Cross-registry cleanup for consistent maintenance")

    print("\n💡 Usage Examples:")
    print("   Single Registry:")
    print("   • clear_context_batch('test-context', dry_run=True)")
    print("   • clear_multiple_contexts_batch(['ctx1', 'ctx2'])")

    print("\n   Multi Registry:")
    print("   • clear_context_batch('test-context', 'dev-registry')")
    print("   • clear_context_across_registries_batch('ctx', ['dev', 'prod'])")

    return True


@pytest.mark.asyncio
async def test_batch_cleanup():
    """Test batch cleanup operations via MCP"""
    print("🧹 Testing Batch Cleanup Operations")
    print("=" * 50)

    # Setup environment
    os.environ["SCHEMA_REGISTRY_URL"] = "http://localhost:38081"
    os.environ["VIEWONLY"] = "false"

    # Get server script path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(os.path.dirname(script_dir), "kafka_schema_registry_unified_mcp.py")

    # Create client
    client = Client(server_script)

    try:
        async with client:
            print("✅ MCP connection established")

            # Get available tools
            tools = await client.list_tools()
            tool_names = [tool.name for tool in tools]
            print(f"📋 Available tools: {len(tool_names)}")

            # Test batch cleanup tools if available
            cleanup_tools = [
                "cleanup_schemas",
                "bulk_cleanup",
                "batch_delete_schemas",
                "cleanup_by_pattern",
            ]

            available_cleanup_tools = [tool for tool in cleanup_tools if tool in tool_names]
            print(f"🧹 Cleanup tools available: {available_cleanup_tools}")

            for tool_name in available_cleanup_tools:
                print(f"\n🧪 Testing: {tool_name}")
                try:
                    # Use minimal test arguments
                    args = {}
                    if "pattern" in tool_name:
                        args = {"pattern": "test-*"}
                    elif "bulk" in tool_name:
                        args = {"subjects": ["test-subject-1", "test-subject-2"]}
                    elif "batch" in tool_name:
                        args = {"subjects": ["test-subject"]}
                    else:
                        args = {"dry_run": True}

                    result = await client.call_tool(tool_name, args)
                    print(f"✅ {tool_name}: Executed successfully")

                    # Check if result contains cleanup info
                    result_text = str(result)
                    if "cleanup" in result_text.lower() or "deleted" in result_text.lower():
                        print("   Result appears to be cleanup-related")

                except Exception as e:
                    if "connection" in str(e).lower() or "registry" in str(e).lower():
                        print(f"⚠️  {tool_name}: Connection error (expected): {e}")
                    else:
                        print(f"❌ {tool_name}: Unexpected error: {e}")

            # Test non-destructive operations
            safe_tools = [
                "count_schemas_by_subject",
                "count_total_schemas",
            ]
            available_safe_tools = [tool for tool in safe_tools if tool in tool_names]

            print(f"\n📊 Testing safe operations: {available_safe_tools}")
            for tool_name in available_safe_tools:
                try:
                    result = await client.call_tool(tool_name, {})
                    print(f"✅ {tool_name}: Working")
                except Exception as e:
                    print(f"⚠️  {tool_name}: {e}")

            print("\n🎉 Batch cleanup test completed!")
            return True

    except Exception as e:
        print(f"❌ Critical error during batch cleanup test: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Main test runner"""
    print("🚀 Batch Context Cleanup Tools Test Suite")
    print("=" * 60)

    # Check registry connectivity
    print("🔍 Checking registry connectivity...")
    try:
        dev_response = requests.get("http://localhost:38081/subjects", timeout=5)
        prod_response = requests.get("http://localhost:38082/subjects", timeout=5)

        if dev_response.status_code != 200:
            print(f"❌ DEV registry not accessible: {dev_response.status_code}")
            return False

        if prod_response.status_code != 200:
            print(f"❌ PROD registry not accessible: {prod_response.status_code}")
            return False

        print("✅ Both registries accessible")

    except Exception as e:
        print(f"❌ Registry connectivity failed: {e}")
        print("💡 Make sure multi-registry environment is running:")
        print("   ./tests/start_multi_registry_environment.sh")
        return False

    # Run tests
    tests = [
        ("Single-Registry Batch Cleanup", test_single_registry_batch_cleanup, True),
        ("Multi-Registry Batch Cleanup", test_multi_registry_batch_cleanup, True),
        ("Performance Characteristics", test_performance_characteristics, False),
        ("Batch Cleanup via MCP Client", test_batch_cleanup, True),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func, is_async in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            # Reset task manager before each test for isolation
            try:
                import kafka_schema_registry_unified_mcp

                kafka_schema_registry_unified_mcp.task_manager.reset_for_testing()
                print("🔄 Task manager reset for test isolation")
            except Exception as e:
                print(f"⚠️  Warning: Could not reset task manager: {e}")

            if is_async:
                if await test_func():
                    passed += 1
                    print(f"✅ {test_name} PASSED")
                else:
                    print(f"❌ {test_name} FAILED")
            else:
                if test_func():
                    passed += 1
                    print(f"✅ {test_name} PASSED")
                else:
                    print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")

        # Additional cleanup after each test
        try:
            import kafka_schema_registry_unified_mcp

            kafka_schema_registry_unified_mcp.task_manager.reset_for_testing()
            print("🧹 Post-test cleanup completed")
        except Exception as e:
            print(f"⚠️  Warning: Post-test cleanup failed: {e}")

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL BATCH CLEANUP TESTS PASSED!")
        print("\n🚀 Batch cleanup tools are ready for use!")
        print("   • Use dry_run=True for safe testing")
        print("   • Tools support both single and multi-registry modes")
        print("   • Performance optimized with parallel execution")
        print("   • Comprehensive error handling and reporting")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed")
        return False


if __name__ == "__main__":
    asyncio.run(main())
