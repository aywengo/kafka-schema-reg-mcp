#!/usr/bin/env python3
"""
Test script for the Kafka Schema Registry MCP Server

This script demonstrates how to connect to and test the MCP server
using the official MCP Python SDK client.
"""

import asyncio
import json
import os
import sys

from fastmcp import Client


async def test_mcp_server():
    """Test the MCP server functionality."""

    # Path to the unified server script
    server_script = "kafka_schema_registry_unified_mcp.py"

    # Environment variables for the server
    env = {
        "SCHEMA_REGISTRY_URL": "http://localhost:38081",  # Actual Schema Registry port
        "SCHEMA_REGISTRY_USER": "",
        "SCHEMA_REGISTRY_PASSWORD": "",
    }

    # Update the current environment
    for key, value in env.items():
        os.environ[key] = value

    print("🚀 Starting MCP Server test...")
    print(f"🔍 Python version: {sys.version}")
    print(f"📁 Current directory: {os.getcwd()}")

    try:
        # Create client that will run the server script
        client = Client(server_script)

        # Add timeout to prevent hanging
        async with client:
            print("📡 Connection established successfully!")

            # List available tools
            print("\n🔧 Available tools:")
            tools = await client.list_tools()
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")

            # List available resources
            print("\n📦 Available resources:")
            resources = await client.list_resources()
            for resource in resources:
                print(f"  - {resource.uri}: {resource.description}")

            # Test a simple resource read first - check server status
            print("\n🔍 Testing server status...")
            try:
                result = await client.read_resource("registry://status")
                print(f"✅ Server status: {result[0].text}")
            except Exception as e:
                print(f"⚠️ Server status check failed: {e}")

            # Test basic tool call (list_subjects is simple and safe)
            print("\n📄 Testing basic tool call (list_subjects)...")
            try:
                result = await client.call_tool("list_subjects", {})
                print(f"✅ Tool call successful: {len(result)} items")
                if result:
                    print(f"📋 Response: {result[0].text[:200]}...")
            except Exception as e:
                print(
                    f"⚠️ Tool call failed (might be expected if no schema registry): {e}"
                )

            print("\n✅ MCP Server basic connectivity test completed!")

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback

        traceback.print_exc()
        raise


async def test_dependencies():
    """Test if required dependencies are available."""
    print("🔍 Checking dependencies...")

    try:
        import fastmcp

        print(
            f"✅ FastMCP available: {fastmcp.__version__ if hasattr(fastmcp, '__version__') else 'Unknown version'}"
        )
    except ImportError as e:
        print(f"❌ FastMCP not available: {e}")
        return False

    try:
        import requests

        print(f"✅ Requests available: {requests.__version__}")
    except ImportError as e:
        print(f"❌ Requests not available: {e}")
        return False

    try:
        import asyncio

        print(f"✅ Asyncio available")
    except ImportError as e:
        print(f"❌ Asyncio not available: {e}")
        return False

    # Check if the unified MCP server file exists
    mcp_server_path = "kafka_schema_registry_unified_mcp.py"
    if os.path.exists(mcp_server_path):
        print(f"✅ Unified MCP server file found: {mcp_server_path}")
    else:
        print(f"❌ Unified MCP server file not found: {mcp_server_path}")
        return False

    return True


async def main():
    """Main function with overall timeout."""
    try:
        # Test dependencies first
        deps_ok = await test_dependencies()
        if not deps_ok:
            print("❌ Dependency check failed, aborting test")
            return

        print("\n" + "=" * 50)
        await asyncio.wait_for(test_mcp_server(), timeout=60)  # 1 minute total timeout
    except asyncio.TimeoutError:
        print("❌ Test timed out after 60 seconds")
        raise
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
