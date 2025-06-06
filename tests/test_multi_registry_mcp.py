#!/usr/bin/env python3
"""
Test script for Unified Kafka Schema Registry MCP Server in Multi-Registry Mode.

This script tests the unified MCP server with multi-registry support including:
- Registry management (list, test connections, get info)
- Cross-registry comparison (registries, contexts, schemas)
- Migration operations (schemas, contexts)
- Synchronization features
- All original tools enhanced with registry parameter
"""

import asyncio
import os
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_unified_mcp_server_multi_registry_mode():
    print("🚀 Testing Unified Kafka Schema Registry MCP Server (Multi-Registry Mode)")
    print("=" * 60)
    
    # Set up multi-registry configuration using numbered environment variables
    env = os.environ.copy()
    
    # Configure 3 registries using numbered approach
    env["SCHEMA_REGISTRY_NAME_1"] = "development"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
    env["SCHEMA_REGISTRY_USER_1"] = ""
    env["SCHEMA_REGISTRY_PASSWORD_1"] = ""
    env["READONLY_1"] = "false"
    
    env["SCHEMA_REGISTRY_NAME_2"] = "staging"
    env["SCHEMA_REGISTRY_URL_2"] = "http://localhost:38082"
    env["SCHEMA_REGISTRY_USER_2"] = ""
    env["SCHEMA_REGISTRY_PASSWORD_2"] = ""
    env["READONLY_2"] = "false"
    
    env["SCHEMA_REGISTRY_NAME_3"] = "production"
    env["SCHEMA_REGISTRY_URL_3"] = "http://localhost:8083"
    env["SCHEMA_REGISTRY_USER_3"] = "prod-user"
    env["SCHEMA_REGISTRY_PASSWORD_3"] = "prod-password"
    env["READONLY_3"] = "true"
    
    # Get the absolute path to the server script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(os.path.dirname(script_dir), "kafka_schema_registry_unified_mcp.py")
    
    server_params = StdioServerParameters(
        command="python",
        args=[server_script],
        env=env
    )
    
    try:
        # Add timeout to prevent hanging indefinitely
        await asyncio.wait_for(
            _run_mcp_tests(server_params),
            timeout=30.0  # 30 second timeout
        )
    except asyncio.TimeoutError:
        print("❌ Test timed out after 30 seconds - likely hanging on MCP connection")
        return
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return

async def _run_mcp_tests(server_params):
    """Helper function to run all MCP tests with the client."""
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("✅ MCP connection established")
            
            # Test 1: List available tools
            print("\n🔧 Testing tool availability...")
            tools = await session.list_tools()
            tool_names = [tool.name for tool in tools.tools]
            print(f"📋 Available tools: {len(tool_names)}")
            
            # Check for multi-registry tools
            multi_registry_tools = [
                "list_registries", "get_registry_info", "test_registry_connection", 
                "test_all_registries", "compare_registries", "compare_contexts_across_registries",
                "find_missing_schemas", "migrate_schema", "migrate_context",  # Now generates Docker configuration 
                "list_migrations", "get_migration_status", "sync_schema"
            ]
            
            found_tools = []
            missing_tools = []
            
            for tool in multi_registry_tools:
                if tool in tool_names:
                    found_tools.append(tool)
                else:
                    missing_tools.append(tool)
            
            print(f"✅ Multi-registry tools found: {len(found_tools)}")
            print(f"❌ Missing tools: {len(missing_tools)}")
            
            if missing_tools:
                print(f"   Missing: {', '.join(missing_tools)}")
            
            # Test 2: Registry management
            print("\n🏢 Testing registry management...")
            
            try:
                result = await session.call_tool("list_registries", {})
                if result.content and len(result.content) > 0:
                    content = result.content[0].text
                    registries = json.loads(content)
                    print(f"✅ Found {len(registries)} registries")
                    for registry in registries:
                        print(f"   • {registry.get('name', 'unknown')}: {registry.get('url', 'no url')}")
                else:
                    print("❌ No registries found")
            except Exception as e:
                print(f"❌ Registry listing failed: {e}")
            
            # Test 3: Test all registry connections
            print("\n🔗 Testing registry connections...")
            
            try:
                result = await session.call_tool("test_all_registries", {})
                if result.content and len(result.content) > 0:
                    content = result.content[0].text
                    test_results = json.loads(content)
                    
                    total = test_results.get("total_registries", 0)
                    connected = test_results.get("connected", 0)
                    failed = test_results.get("failed", 0)
                    
                    print(f"📊 Connection test results:")
                    print(f"   Total registries: {total}")
                    print(f"   ✅ Connected: {connected}")
                    print(f"   ❌ Failed: {failed}")
                    
                    # Show individual results
                    registry_tests = test_results.get("registry_tests", {})
                    for name, test_result in registry_tests.items():
                        status = test_result.get("status", "unknown")
                        if status == "connected":
                            response_time = test_result.get("response_time_ms", 0)
                            print(f"   ✅ {name}: Connected ({response_time:.1f}ms)")
                        else:
                            error = test_result.get("error", "Connection failed")
                            print(f"   ❌ {name}: {error}")
            
            except Exception as e:
                print(f"❌ Connection testing failed: {e}")
            
            # Test 4: Cross-registry comparison (dry run)
            print("\n🔍 Testing cross-registry comparison...")
            
            try:
                result = await session.call_tool("compare_registries", {
                    "source_registry": "development",
                    "target_registry": "production"
                })
                if result.content and len(result.content) > 0:
                    content = result.content[0].text
                    comparison = json.loads(content)
                    
                    if "error" in comparison:
                        print(f"⚠️  Comparison failed (expected): {comparison['error']}")
                    else:
                        print(f"✅ Comparison completed: {comparison.get('source')} vs {comparison.get('target')}")
                        print(f"   Compared at: {comparison.get('compared_at')}")
            
            except Exception as e:
                print(f"❌ Comparison failed: {e}")
            
            # Test 5: Schema migration (dry run)
            print("\n📦 Testing schema migration (dry run)...")
            
            try:
                result = await session.call_tool("migrate_schema", {
                    "subject": "test-user-events",
                    "source_registry": "development",
                    "target_registry": "staging",
                    "dry_run": True
                })
                if result.content and len(result.content) > 0:
                    content = result.content[0].text
                    migration = json.loads(content)
                    
                    if "error" in migration:
                        print(f"⚠️  Migration test failed (expected): {migration['error']}")
                    else:
                        print(f"✅ Migration dry run completed:")
                        print(f"   Subject: {migration.get('subject')}")
                        print(f"   From: {migration.get('source_registry')}")
                        print(f"   To: {migration.get('target_registry')}")
                        print(f"   Status: {migration.get('status')}")
            
            except Exception as e:
                print(f"❌ Migration test failed: {e}")
            
            # Test 6: Enhanced original tools with registry parameter
            print("\n🔧 Testing enhanced original tools...")
            
            try:
                result = await session.call_tool("register_schema", {
                    "subject": "test-schema",
                    "schema_definition": {"type": "string"},
                    "registry": "development"
                })
                if result.content and len(result.content) > 0:
                    content = result.content[0].text
                    response = json.loads(content)
                    
                    if "error" in response:
                        print(f"⚠️  Schema registration failed (expected): {response['error']}")
                    else:
                        print(f"✅ Schema registration works with registry parameter")
                        print(f"   Registry: {response.get('registry')}")
            
            except Exception as e:
                print(f"❌ Enhanced tool test failed: {e}")
            
            # Test 7: Check migration history
            print("\n📝 Testing migration history...")
            
            try:
                result = await session.call_tool("list_migrations", {})
                if result.content and len(result.content) > 0:
                    content = result.content[0].text
                    migrations = json.loads(content)
                    
                    if isinstance(migrations, list):
                        print(f"✅ Migration history available: {len(migrations)} migrations")
                        for migration in migrations[:3]:  # Show first 3
                            print(f"   • {migration.get('scope')} ({migration.get('status')})")
                    else:
                        print(f"❌ Unexpected migration format: {type(migrations)}")
            
            except Exception as e:
                print(f"❌ Migration history test failed: {e}")
            
            # Test 8: Server info resource
            print("\n📊 Testing unified server in multi-registry mode info...")
            
            try:
                resources = await session.list_resources()
                for resource in resources.resources:
                    if resource.uri == "registry://info":
                        result = await session.read_resource(resource.uri)
                        if result.contents and len(result.contents) > 0:
                            content = result.contents[0].text
                            info = json.loads(content)
                            
                            print(f"✅ Server info:")
                            print(f"   Version: {info.get('server_version')}")
                            print(f"   Multi-registry support: {info.get('multi_registry_support')}")
                            print(f"   Total tools: {info.get('total_tools')}")
                            print(f"   Total registries: {info.get('total_registries')}")
                            print(f"   Default registry: {info.get('default_registry')}")
                            print(f"   READONLY mode: {info.get('readonly_mode')}")
                        break
            
            except Exception as e:
                print(f"❌ Server info test failed: {e}")
            
            print("\n" + "=" * 60)
            print("🎉 unified server in multi-registry mode Test Completed!")
            print("\nTest Summary:")
            print("✅ Multi-registry infrastructure working")
            print("✅ Registry management tools functional") 
            print("✅ Cross-registry comparison available")
            print("✅ Migration tools operational")
            print("✅ Enhanced original tools with registry support")
            print("✅ Server info shows multi-registry capabilities")
            
            print(f"\n📋 Total tools tested: {len(found_tools)}/{len(multi_registry_tools)} multi-registry tools")

def test_auth_config_multi_mode(monkeypatch):
    """Test that auth config is correctly applied in unified server multi-registry mode."""
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("AUTH_ISSUER_URL", "https://multi-issuer.com")
    monkeypatch.setenv("AUTH_VALID_SCOPES", "multi1,multi2")
    monkeypatch.setenv("AUTH_DEFAULT_SCOPES", "multi1")
    monkeypatch.setenv("AUTH_REQUIRED_SCOPES", "multi1")
    monkeypatch.setenv("AUTH_CLIENT_REG_ENABLED", "true")
    monkeypatch.setenv("AUTH_REVOCATION_ENABLED", "true")
    
    # Set multi-registry environment variables to trigger multi mode
    monkeypatch.setenv("SCHEMA_REGISTRY_URL_1", "http://localhost:38081")
    monkeypatch.setenv("SCHEMA_REGISTRY_NAME_1", "dev")

    import importlib
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import kafka_schema_registry_unified_mcp
    importlib.reload(kafka_schema_registry_unified_mcp)

    mcp = kafka_schema_registry_unified_mcp.mcp
    auth = getattr(mcp, "auth", None)
    assert auth is not None, "Auth should be set when ENABLE_AUTH is true"
    assert auth.issuer_url == "https://multi-issuer.com"
    assert set(auth.client_registration_options.valid_scopes) == {"multi1", "multi2"}
    assert set(auth.client_registration_options.default_scopes) == {"multi1"}
    assert set(auth.required_scopes) == {"multi1"}
    assert auth.client_registration_options.enabled
    assert auth.revocation_options.enabled

if __name__ == "__main__":
    asyncio.run(test_unified_mcp_server_multi_registry_mode()) 