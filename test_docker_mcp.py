#!/usr/bin/env python3
"""
Test the MCP server running in Docker container
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_docker_mcp_server():
    """Test the MCP server running in Docker."""
    
    # Create server parameters to run via Docker
    server_params = StdioServerParameters(
        command="docker",
        args=[
            "run", 
            "--rm", 
            "-i",
            "--network", "host",
            "-e", "SCHEMA_REGISTRY_URL",
            "kafka-schema-reg-mcp:test"
        ],
        env={
            "SCHEMA_REGISTRY_URL": "http://localhost:38081"
        }
    )

    print("🐳 Testing MCP server in Docker container...")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize connection
                print("📡 Initializing connection...")
                await session.initialize()
                print("✅ Connected to MCP server in Docker!")

                # List available tools
                print("\n🔧 Listing available tools...")
                tools = await session.list_tools()
                print(f"Found {len(tools.tools)} tools:")
                for tool in tools.tools[:5]:  # Show first 5 tools
                    print(f"  - {tool.name}")
                print(f"  ... and {len(tools.tools) - 5} more tools")

                # Test a simple operation
                print("\n📋 Testing list_contexts...")
                try:
                    result = await session.call_tool("list_contexts", {})
                    print(f"Contexts result: {result.content[0].text}")
                    print("✅ Docker MCP server working correctly!")
                except Exception as e:
                    print(f"Context listing (expected if no Schema Registry): {e}")
                    print("✅ Docker container and MCP protocol working!")

                print("\n🎉 Docker MCP server test completed successfully!")

    except Exception as e:
        print(f"❌ Error during Docker test: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_docker_mcp_server()) 