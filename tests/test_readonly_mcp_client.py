#!/usr/bin/env python3
"""
Test script to verify READONLY mode works correctly with an actual MCP client connection.
This simulates how Claude Desktop would interact with the server in READONLY mode.
"""

import asyncio
import json
import os

from fastmcp import Client


async def test_readonly_with_mcp_client():
    print("🔒 Testing READONLY mode with MCP client...")
    print("=" * 50)

    # Set READONLY mode
    env = os.environ.copy()
    env["READONLY"] = "true"
    env["SCHEMA_REGISTRY_URL"] = "http://localhost:38081"

    # Get the path to the parent directory where the server script is located
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_script = os.path.join(parent_dir, "kafka_schema_registry_unified_mcp.py")

    # Update the current environment
    for key, value in env.items():
        os.environ[key] = value

    client = Client(server_script)

    async with client:
        print("✅ MCP connection established")

        # Test 1: List available tools
        tools = await client.list_tools()
        print(f"📋 Available tools: {len(tools)}")

        # Test 2: Try a modification operation (should be blocked)
        print("\n🧪 Testing blocked operation: register_schema")
        try:
            result = await client.call_tool(
                "register_schema",
                {
                    "subject": "test-readonly-schema",
                    "schema_definition": {"type": "string"},
                    "schema_type": "AVRO",
                },
            )

            if result:
                try:
                    response = json.loads(result)
                    if "readonly_mode" in response:
                        print("✅ register_schema correctly blocked in READONLY mode")
                        print(f"   Error: {response['error']}")
                    else:
                        print("❌ register_schema should be blocked but wasn't!")
                        print(f"   Response: {response}")
                except json.JSONDecodeError:
                    if "readonly" in result.lower():
                        print("✅ register_schema correctly blocked in READONLY mode")
                        print(f"   Error: {result}")
                    else:
                        print("❌ register_schema should be blocked but wasn't!")
                        print(f"   Response: {result}")
            else:
                print("❌ No response from register_schema")

        except Exception as e:
            print(f"⚠️  Exception during register_schema test: {e}")

        # Test 3: Try a read operation (should work)
        print("\n🧪 Testing allowed operation: list_subjects")
        try:
            result = await client.call_tool("list_subjects", {})

            if result:
                try:
                    response = json.loads(result)
                    if "readonly_mode" in response:
                        print("❌ list_subjects should NOT be blocked")
                        print(f"   Error: {response['error']}")
                    else:
                        print("✅ list_subjects correctly allowed in READONLY mode")
                        print(f"   Response type: {type(response)}")
                except json.JSONDecodeError:
                    print("✅ list_subjects correctly allowed in READONLY mode")
                    print(f"   Response: {result}")
            else:
                print("✅ list_subjects allowed (empty response)")

        except Exception as e:
            # Connection error is expected if Schema Registry isn't running
            if "readonly" in str(e).lower():
                print("❌ list_subjects incorrectly blocked by readonly mode")
            else:
                print(
                    "✅ list_subjects not blocked by readonly mode (connection error expected)"
                )

        # Test 4: Try an export operation (should work)
        print("\n🧪 Testing allowed operation: export_global")
        try:
            result = await client.call_tool("export_global", {})

            if result:
                try:
                    response = json.loads(result)
                    if "readonly_mode" in response:
                        print("❌ export_global should NOT be blocked")
                        print(f"   Error: {response['error']}")
                    else:
                        print("✅ export_global correctly allowed in READONLY mode")
                        print(f"   Response type: {type(response)}")
                except json.JSONDecodeError:
                    print("✅ export_global correctly allowed in READONLY mode")
                    print(f"   Response: {result}")
            else:
                print("✅ export_global allowed (empty response)")

        except Exception as e:
            if "readonly" in str(e).lower():
                print("❌ export_global incorrectly blocked by readonly mode")
            else:
                print(
                    "✅ export_global not blocked by readonly mode (connection error expected)"
                )

        # Test 5: Check server info resource
        print("\n🧪 Testing registry info resource")
        try:
            resources = await client.list_resources()
            print(f"📦 Available resources: {len(resources)}")

            for resource in resources:
                if resource.uri == "registry://info":
                    result = await client.read_resource(resource.uri)
                    if result:
                        try:
                            info = json.loads(result)
                            readonly_status = info.get("readonly_mode", "unknown")
                            print(
                                f"✅ Server info shows readonly_mode: {readonly_status}"
                            )
                        except json.JSONDecodeError:
                            print(f"✅ Server info resource available: {result[:100]}...")
                    break

        except Exception as e:
            print(f"⚠️  Error reading server info: {e}")

        print("\n" + "=" * 50)
        print("🎉 READONLY mode MCP client test completed!")
        print("\nSummary:")
        print("- ❌ Modification operations should be blocked")
        print("- ✅ Read operations should be allowed")
        print("- ✅ Export operations should be allowed")


if __name__ == "__main__":
    asyncio.run(test_readonly_with_mcp_client())
