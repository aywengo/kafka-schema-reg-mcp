#!/usr/bin/env python3
"""
Test script for the Kafka Schema Registry MCP Server

This script demonstrates how to connect to and test the MCP server
using the official MCP Python SDK client.
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcp_server():
    """Test the MCP server functionality."""
    
    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command="python",
        args=["kafka_schema_registry_mcp.py"],
        env={
            "SCHEMA_REGISTRY_URL": "http://localhost:38081",
            "SCHEMA_REGISTRY_USER": "",
            "SCHEMA_REGISTRY_PASSWORD": ""
        }
    )

    print("🚀 Starting MCP Server test...")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                print("📡 Initializing connection...")
                await session.initialize()
                print("✅ Connection initialized successfully!")

                # List available tools
                print("\n🔧 Available tools:")
                tools = await session.list_tools()
                for tool in tools.tools:
                    print(f"  - {tool.name}: {tool.description}")

                # List available resources
                print("\n📦 Available resources:")
                resources = await session.list_resources()
                for resource in resources.resources:
                    print(f"  - {resource.uri}: {resource.description}")

                # Test registry status resource
                print("\n🔍 Testing registry status resource...")
                try:
                    content, mime_type = await session.read_resource("registry://status")
                    print(f"Registry Status: {content.text}")
                except Exception as e:
                    print(f"❌ Error reading registry status: {e}")

                # Test registry info resource
                print("\n📋 Testing registry info resource...")
                try:
                    content, mime_type = await session.read_resource("registry://info")
                    print(f"Registry Info: {content.text}")
                except Exception as e:
                    print(f"❌ Error reading registry info: {e}")

                # Test list contexts tool
                print("\n🗂️ Testing list_contexts tool...")
                try:
                    result = await session.call_tool("list_contexts", arguments={})
                    print(f"Contexts: {result.content}")
                except Exception as e:
                    print(f"❌ Error calling list_contexts: {e}")

                # Test list subjects tool
                print("\n📄 Testing list_subjects tool...")
                try:
                    result = await session.call_tool("list_subjects", arguments={})
                    print(f"Subjects: {result.content}")
                except Exception as e:
                    print(f"❌ Error calling list_subjects: {e}")

                # Test schema registration (example)
                print("\n📝 Testing schema registration...")
                try:
                    sample_schema = {
                        "type": "record",
                        "name": "TestUser",
                        "fields": [
                            {"name": "id", "type": "int"},
                            {"name": "name", "type": "string"},
                            {"name": "email", "type": "string"}
                        ]
                    }
                    
                    result = await session.call_tool("register_schema", arguments={
                        "subject": "test-user-value",
                        "schema": sample_schema,
                        "schema_type": "AVRO"
                    })
                    print(f"Schema registration result: {result.content}")
                except Exception as e:
                    print(f"❌ Error registering schema: {e}")

                print("\n✅ MCP Server test completed!")

    except Exception as e:
        print(f"❌ Error during test: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_mcp_server()) 