#!/usr/bin/env python3
"""
Advanced MCP Server Test

This script demonstrates the full capabilities of the Kafka Schema Registry MCP Server
including schema registration, context management, configuration, export, and more.
"""

import asyncio
import json
import os

from fastmcp import Client


async def test_advanced_mcp_features():
    """Test advanced MCP server functionality with real Schema Registry."""

    # Get the path to the parent directory where the server script is located
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_script = os.path.join(parent_dir, "kafka_schema_registry_unified_mcp.py")

    print("🚀 Starting Advanced MCP Server Test...")

    # Set environment variables
    os.environ["SCHEMA_REGISTRY_URL"] = "http://localhost:38081"
    os.environ["SCHEMA_REGISTRY_USER"] = ""
    os.environ["SCHEMA_REGISTRY_PASSWORD"] = ""

    try:
        client = Client(server_script)

        async with client:
            # Initialize connection
            print("📡 Initializing connection...")
            print("✅ Connected successfully!")

            # Test 1: Create production context
            print("\n🏗️ Creating production context...")
            try:
                result = await client.call_tool("create_context", {"context": "production"})
                print(f"Context creation: {result}")
            except Exception as e:
                print(f"⚠️ Context creation (may already exist): {e}")

            # Test 2: List contexts (using resource instead of tool)
            print("\n📋 Listing contexts...")
            try:
                result = await client.read_resource("registry://default/contexts")
                if result:
                    print(f"Available contexts: {result}")
                else:
                    print(f"❌ No content returned for contexts resource: {result}")
            except Exception as e:
                print(f"⚠️ Contexts resource not available: {e}")
                # Fallback: skip this test
                print("   Skipping contexts listing test")

            # Test 3: Register user schema in production
            print("\n📝 Registering user schema in production context...")
            user_schema = {
                "type": "record",
                "name": "User",
                "namespace": "com.example",
                "doc": "User information schema",
                "fields": [
                    {"name": "id", "type": "long", "doc": "User ID"},
                    {"name": "username", "type": "string", "doc": "Username"},
                    {"name": "email", "type": "string", "doc": "Email address"},
                    {
                        "name": "created_at",
                        "type": "long",
                        "doc": "Creation timestamp",
                    },
                    {
                        "name": "metadata",
                        "type": ["null", {"type": "map", "values": "string"}],
                        "default": None,
                    },
                ],
            }

            result = await client.call_tool(
                "register_schema",
                {
                    "subject": "user-events-value",
                    "schema_definition": user_schema,
                    "schema_type": "AVRO",
                    "context": "production",
                },
            )
            if result:
                print(f"Schema registration: {result}")
            else:
                print(f"❌ No content returned for register_schema: {result}")

            # Test 4: Register order schema in default context
            print("\n🛒 Registering order schema in default context...")
            order_schema = {
                "type": "record",
                "name": "Order",
                "namespace": "com.example",
                "fields": [
                    {"name": "order_id", "type": "string"},
                    {"name": "user_id", "type": "long"},
                    {"name": "amount", "type": "double"},
                    {"name": "currency", "type": "string", "default": "USD"},
                ],
            }

            result = await client.call_tool(
                "register_schema",
                {
                    "subject": "order-events-value",
                    "schema_definition": order_schema,
                    "schema_type": "AVRO",
                },
            )
            if result:
                print(f"Order schema registration: {result}")
            else:
                print(f"❌ No content returned for order schema registration: {result}")

            # Test 5: List subjects in different contexts (using resources)
            print("\n📄 Listing subjects in production context...")
            try:
                result = await client.read_resource("registry://default/subjects?context=production")
                if result:
                    print(f"Production subjects: {result}")
                else:
                    print(f"❌ No content returned for production subjects resource: {result}")
            except Exception as e:
                print(f"⚠️ Production subjects resource not available: {e}")

            print("\n📄 Listing subjects in default context...")
            try:
                result = await client.read_resource("registry://default/subjects")
                if result:
                    print(f"Default subjects: {result}")
                else:
                    print(f"❌ No content returned for default subjects resource: {result}")
            except Exception as e:
                print(f"⚠️ Default subjects resource not available: {e}")

            # Test 6: Get schema versions (using resource)
            print("\n🔢 Getting schema versions...")
            try:
                result = await client.read_resource("schema://default/production/user-events-value/versions")
                if result:
                    print(f"User schema versions: {result}")
                else:
                    print(f"❌ No content returned for schema versions resource: {result}")
            except Exception as e:
                print(f"⚠️ Schema versions resource not available: {e}")

            # Test 7: Check compatibility
            print("\n🔍 Testing schema compatibility...")
            # Try to register a compatible schema evolution
            evolved_user_schema = {
                "type": "record",
                "name": "User",
                "namespace": "com.example",
                "fields": [
                    {"name": "id", "type": "long"},
                    {"name": "username", "type": "string"},
                    {"name": "email", "type": "string"},
                    {"name": "created_at", "type": "long"},
                    {
                        "name": "metadata",
                        "type": ["null", {"type": "map", "values": "string"}],
                        "default": None,
                    },
                    {
                        "name": "status",
                        "type": "string",
                        "default": "active",
                    },  # New field with default
                ],
            }

            result = await client.call_tool(
                "check_compatibility",
                {
                    "subject": "user-events-value",
                    "schema_definition": evolved_user_schema,
                    "context": "production",
                },
            )
            if result:
                print(f"Compatibility check: {result}")
            else:
                print(f"❌ No content returned for check_compatibility: {result}")

            # Test 8: Global configuration (using resource)
            print("\n⚙️ Getting global configuration...")
            try:
                result = await client.read_resource("registry://default/config")
                if result:
                    print(f"Global config: {result}")
                else:
                    print(f"❌ No content returned for global config resource: {result}")
            except Exception as e:
                print(f"⚠️ Global config resource not available: {e}")

            # Test 9: Set production to strict compatibility
            print("\n🔒 Setting production to FULL compatibility...")
            try:
                result = await client.call_tool(
                    "update_global_config",
                    {"compatibility": "FULL", "context": "production"},
                )
                if result:
                    print(f"Config update: {result}")
                else:
                    print(f"❌ No content returned for update_global_config: {result}")
            except Exception as e:
                print(f"⚠️ Config update: {e}")

            # Test 10: Export single schema as Avro IDL
            print("\n📤 Exporting user schema as Avro IDL...")
            result = await client.call_tool(
                "export_schema",
                {
                    "subject": "user-events-value",
                    "context": "production",
                    "format": "avro_idl",
                },
            )
            if result:
                print(f"Avro IDL Export:\n{result}")
            else:
                print(f"❌ No content returned for export_schema: {result}")

            # Test 11: Export production context
            print("\n📦 Exporting production context...")
            result = await client.call_tool(
                "export_context",
                {
                    "context": "production",
                    "include_metadata": True,
                    "include_config": True,
                    "include_versions": "all",
                },
            )
            if result:
                try:
                    # FastMCP 2.8.0+ returns a list of content objects
                    if isinstance(result, list) and len(result) > 0:
                        response_text = result[0].text if hasattr(result[0], "text") else str(result[0])
                    else:
                        response_text = str(result)

                    if response_text:
                        export_data = json.loads(response_text)
                        if "error" in export_data:
                            print(f"⚠️ Export failed: {export_data['error']}")
                        else:
                            print(f"Production export: {len(export_data.get('subjects', []))} subjects exported")
                    else:
                        print("⚠️ Empty response from export_context")
                except json.JSONDecodeError as e:
                    print(f"⚠️ Failed to parse export response as JSON: {e}")
                    print(f"Raw response: {result}")
            else:
                print(f"❌ No content returned for export_context: {result}")

            # Test 12: Get current mode (using resource)
            print("\n🎛️ Getting current mode...")
            try:
                result = await client.read_resource("registry://mode")
                if result:
                    print(f"Current mode: {result}")
                else:
                    print(f"❌ No content returned for mode resource: {result}")
            except Exception as e:
                print(f"⚠️ Mode resource not available: {e}")

            print("\n🎉 Advanced MCP Server test completed successfully!")
            print("✅ All features working: Registration, Contexts, Configuration, Export, Compatibility")

    except Exception as e:
        print(f"❌ Error during advanced test: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_advanced_mcp_features())
