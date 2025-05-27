#!/usr/bin/env python3
"""
Test script to verify both single and multi-registry configuration modes.
"""

import asyncio
import os
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_single_registry_mode():
    print("🔧 Testing Single Registry Mode")
    print("-" * 40)
    
    # Single registry configuration
    env = os.environ.copy()
    env["SCHEMA_REGISTRY_URL"] = "http://localhost:38081"
    env["SCHEMA_REGISTRY_USER"] = "test-user"
    env["SCHEMA_REGISTRY_PASSWORD"] = "test-password"
    env["READONLY"] = "false"
    
    # Clear any multi-registry variables
    for i in range(1, 9):
        env.pop(f"SCHEMA_REGISTRY_NAME_{i}", None)
        env.pop(f"SCHEMA_REGISTRY_URL_{i}", None)
    
    server_params = StdioServerParameters(
        command="python",
        args=["../kafka_schema_registry_multi_mcp.py"],
        env=env
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Test registry listing
                result = await session.call_tool("list_registries", {})
                if result.content and len(result.content) > 0:
                    content = result.content[0].text
                    registries = json.loads(content)
                    print(f"✅ Single mode: Found {len(registries)} registry")
                    for registry in registries:
                        print(f"   • {registry.get('name')}: {registry.get('url')}")
                        print(f"     Readonly: {registry.get('readonly', False)}")
                
                # Test server info
                resources = await session.list_resources()
                for resource in resources.resources:
                    if resource.uri == "registry://info":
                        result = await session.read_resource(resource.uri)
                        if result.contents and len(result.contents) > 0:
                            content = result.contents[0].text
                            info = json.loads(content)
                            print(f"✅ Configuration mode: {info.get('configuration_mode')}")
                            print(f"   Total registries: {info.get('total_registries')}")
                            print(f"   Default registry: {info.get('default_registry')}")
                        break
                
    except Exception as e:
        print(f"❌ Single registry test failed: {e}")

async def test_multi_registry_mode():
    print("\n🔧 Testing Multi-Registry Mode")
    print("-" * 40)
    
    # Multi-registry configuration
    env = os.environ.copy()
    
    # Clear single registry variables
    env.pop("SCHEMA_REGISTRY_URL", None)
        
    # Set up numbered registries
    env["SCHEMA_REGISTRY_NAME_1"] = "development"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
    env["SCHEMA_REGISTRY_USER_1"] = "dev-user"
    env["SCHEMA_REGISTRY_PASSWORD_1"] = "dev-pass"
    env["READONLY_1"] = "false"
    
    env["SCHEMA_REGISTRY_NAME_2"] = "production"
    env["SCHEMA_REGISTRY_URL_2"] = "http://localhost:8083"
    env["SCHEMA_REGISTRY_USER_2"] = "prod-user"
    env["SCHEMA_REGISTRY_PASSWORD_2"] = "prod-pass"
    env["READONLY_2"] = "true"
    
    server_params = StdioServerParameters(
        command="python",
        args=["../kafka_schema_registry_multi_mcp.py"],
        env=env
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Test registry listing
                result = await session.call_tool("list_registries", {})
                if result.content and len(result.content) > 0:
                    content = result.content[0].text
                    registries = json.loads(content)
                    print(f"✅ Multi mode: Found {len(registries)} registries")
                    for registry in registries:
                        print(f"   • {registry.get('name')}: {registry.get('url')}")
                        print(f"     Readonly: {registry.get('readonly', False)}")
                
                # Test per-registry readonly
                try:
                    result = await session.call_tool("register_schema", {
                        "subject": "test-schema",
                        "schema_definition": {"type": "string"},
                        "registry": "production"
                    })
                    if result.content and len(result.content) > 0:
                        content = result.content[0].text
                        response = json.loads(content)
                        if "readonly_mode" in response:
                            print(f"✅ Per-registry READONLY working: {response.get('registry', 'production')} is protected")
                        else:
                            print(f"❌ Per-registry READONLY not working")
                except Exception as e:
                    print(f"⚠️  READONLY test: {e}")
                
                # Test server info
                resources = await session.list_resources()
                for resource in resources.resources:
                    if resource.uri == "registry://info":
                        result = await session.read_resource(resource.uri)
                        if result.contents and len(result.contents) > 0:
                            content = result.contents[0].text
                            info = json.loads(content)
                            print(f"✅ Configuration mode: {info.get('configuration_mode')}")
                            print(f"   Total registries: {info.get('total_registries')}")
                            print(f"   Default registry: {info.get('default_registry')}")
                            print(f"   Max supported: {info.get('max_registries_supported')}")
                        break
                
    except Exception as e:
        print(f"❌ Multi-registry test failed: {e}")

async def main():
    print("🧪 Testing Numbered Environment Variable Configuration")
    print("=" * 60)
    
    await test_single_registry_mode()
    await test_multi_registry_mode()
    
    print("\n" + "=" * 60)
    print("🎉 Configuration Testing Complete!")
    print("\n📋 Configuration Options:")
    print("✅ Single Registry: Use SCHEMA_REGISTRY_URL, SCHEMA_REGISTRY_USER, etc.")
    print("✅ Multi-Registry: Use SCHEMA_REGISTRY_NAME_X, SCHEMA_REGISTRY_URL_X, etc.")
    print("✅ Per-Registry READONLY: Use READONLY_X for each registry")
    print("✅ Maximum 8 registries supported")

if __name__ == "__main__":
    asyncio.run(main()) 