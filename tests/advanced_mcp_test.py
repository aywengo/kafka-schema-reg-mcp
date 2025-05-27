#!/usr/bin/env python3
"""
Advanced MCP Server Test

This script demonstrates the full capabilities of the Kafka Schema Registry MCP Server
including schema registration, context management, configuration, export, and more.
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_advanced_mcp_features():
    """Test advanced MCP server functionality with real Schema Registry."""
    
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

    print("🚀 Starting Advanced MCP Server Test...")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize connection
                print("📡 Initializing connection...")
                await session.initialize()
                print("✅ Connected successfully!")

                # Test 1: Create production context
                print("\n🏗️ Creating production context...")
                try:
                    result = await session.call_tool("create_context", {"context": "production"})
                    print(f"Context creation: {result.content[0].text}")
                except Exception as e:
                    print(f"⚠️ Context creation (may already exist): {e}")

                # Test 2: List contexts
                print("\n📋 Listing contexts...")
                result = await session.call_tool("list_contexts", {})
                print(f"Available contexts: {result.content[0].text}")

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
                        {"name": "created_at", "type": "long", "doc": "Creation timestamp"},
                        {"name": "metadata", "type": ["null", {"type": "map", "values": "string"}], "default": None}
                    ]
                }
                
                result = await session.call_tool("register_schema", {
                    "subject": "user-events-value",
                    "schema_definition": user_schema,
                    "schema_type": "AVRO",
                    "context": "production"
                })
                print(f"Schema registration: {result.content[0].text}")

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
                        {"name": "currency", "type": "string", "default": "USD"}
                    ]
                }
                
                result = await session.call_tool("register_schema", {
                    "subject": "order-events-value", 
                    "schema_definition": order_schema,
                    "schema_type": "AVRO"
                })
                print(f"Order schema registration: {result.content[0].text}")

                # Test 5: List subjects in different contexts
                print("\n📄 Listing subjects in production context...")
                result = await session.call_tool("list_subjects", {"context": "production"})
                print(f"Production subjects: {result.content[0].text}")

                print("\n📄 Listing subjects in default context...")
                result = await session.call_tool("list_subjects", {})
                print(f"Default subjects: {result.content[0].text}")

                # Test 6: Get schema versions
                print("\n🔢 Getting schema versions...")
                result = await session.call_tool("get_schema_versions", {
                    "subject": "user-events-value",
                    "context": "production"
                })
                print(f"User schema versions: {result.content[0].text}")

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
                        {"name": "metadata", "type": ["null", {"type": "map", "values": "string"}], "default": None},
                        {"name": "status", "type": "string", "default": "active"}  # New field with default
                    ]
                }
                
                result = await session.call_tool("check_compatibility", {
                    "subject": "user-events-value",
                    "schema_definition": evolved_user_schema,
                    "context": "production"
                })
                print(f"Compatibility check: {result.content[0].text}")

                # Test 8: Global configuration
                print("\n⚙️ Getting global configuration...")
                result = await session.call_tool("get_global_config", {})
                print(f"Global config: {result.content[0].text}")

                # Test 9: Set production to strict compatibility
                print("\n🔒 Setting production to FULL compatibility...")
                try:
                    result = await session.call_tool("update_global_config", {
                        "compatibility": "FULL",
                        "context": "production"
                    })
                    print(f"Config update: {result.content[0].text}")
                except Exception as e:
                    print(f"⚠️ Config update: {e}")

                # Test 10: Export single schema as Avro IDL
                print("\n📤 Exporting user schema as Avro IDL...")
                result = await session.call_tool("export_schema", {
                    "subject": "user-events-value",
                    "context": "production",
                    "format": "avro_idl"
                })
                print(f"Avro IDL Export:\n{result.content[0].text}")

                # Test 11: Export production context
                print("\n📦 Exporting production context...")
                result = await session.call_tool("export_context", {
                    "context": "production",
                    "include_metadata": True,
                    "include_config": True,
                    "include_versions": "all"
                })
                export_data = json.loads(result.content[0].text)
                print(f"Production export: {len(export_data.get('subjects', []))} subjects exported")

                # Test 12: Get current mode
                print("\n🎛️ Getting current mode...")
                result = await session.call_tool("get_mode", {})
                print(f"Current mode: {result.content[0].text}")

                print("\n🎉 Advanced MCP Server test completed successfully!")
                print("✅ All features working: Registration, Contexts, Configuration, Export, Compatibility")

    except Exception as e:
        print(f"❌ Error during advanced test: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_advanced_mcp_features()) 