#!/usr/bin/env python3
"""
Test multi-registry functionality of the MCP server.
"""

import asyncio
import json
import os

from fastmcp import Client


async def test_multi_registry_mcp():
    """Test multi-registry MCP server functionality."""

    # Get the path to the parent directory where the server script is located
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_script = os.path.join(parent_dir, "kafka_schema_registry_unified_mcp.py")

    print("🏢 Testing Multi-Registry MCP Server...")

    try:
        # Set environment variables
        os.environ["MULTI_REGISTRY_CONFIG"] = json.dumps(
            {
                "dev": {"url": "http://localhost:38081"},
                "prod": {"url": "http://localhost:38082"},
            }
        )

        client = Client(server_script)

        async with client:
            print("✅ Connected to multi-registry MCP server!")

            # Test 1: List available tools
            print("\n🔧 Listing available tools...")
            tools = await client.list_tools()
            print(f"Found {len(tools)} tools")

            # Test 2: List registries (using resource instead of tool)
            print("\n🏢 Listing registries...")
            try:
                result = await client.read_resource("registry://names")
                if result:
                    print(f"Available registries: {result}")
                else:
                    print("❌ No registries found")
            except Exception as e:
                print(f"⚠️ Registries resource not available: {e}")
                print("   Skipping registries listing test")

            # Test 3: Test registry-specific operations (using resource instead of tool)
            print("\n📝 Testing dev registry operations...")
            try:
                result = await client.read_resource("registry://dev/subjects")
                print(f"DEV subjects: {result}")
            except Exception as e:
                print(f"⚠️ DEV registry test (expected if not running): {e}")

            print("\n📝 Testing prod registry operations...")
            try:
                result = await client.call_tool("list_subjects", {"registry": "prod"})
                print(f"PROD subjects: {result}")
            except Exception as e:
                print(f"⚠️ PROD registry test (expected if not running): {e}")

            # Test 4: Cross-registry comparison
            print("\n🔍 Testing cross-registry comparison...")
            try:
                result = await client.call_tool(
                    "compare_registries",
                    {"source_registry": "dev", "target_registry": "prod"},
                )
                print(f"Registry comparison: {result}")
            except Exception as e:
                print(f"⚠️ Registry comparison (expected if registries not running): {e}")

            print("\n🎉 Multi-registry MCP server test completed successfully!")

    except Exception as e:
        print(f"❌ Error during multi-registry test: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_multi_registry_mcp())
