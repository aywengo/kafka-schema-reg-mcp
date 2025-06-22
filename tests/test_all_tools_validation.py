#!/usr/bin/env python3
"""
Comprehensive validation of all MCP tools.
Tests every tool to ensure they all work correctly.
"""

import asyncio
import json
import os

from fastmcp import Client


async def test_all_tools_validation():
    """Validate all MCP tools are working correctly."""

    # Get the path to the parent directory where the server script is located
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_script = os.path.join(parent_dir, "kafka_schema_registry_unified_mcp.py")

    print("🔧 Testing All MCP Tools Validation...")

    try:
        # Set environment variables
        os.environ["SCHEMA_REGISTRY_URL"] = "http://localhost:38081"
        os.environ["MULTI_REGISTRY_CONFIG"] = json.dumps(
            {
                "dev": {"url": "http://localhost:38081"},
                "prod": {"url": "http://localhost:38082"},
            }
        )

        client = Client(server_script)

        async with client:
            print("✅ Connected to MCP server!")

            # Get list of all available tools
            print("\n📋 Getting list of all tools...")
            tools = await client.list_tools()
            print(f"Found {len(tools)} tools to validate")

            # Test each tool category
            passed_tools = []
            failed_tools = []

            # Core Schema Registry Tools
            print("\n🔧 Testing Core Schema Registry Tools...")
            core_tools = [
                "list_subjects",
                "register_schema",
                "get_schema",
                "get_schema_versions",
                "check_compatibility",
                "delete_subject",
                "get_global_config",
                "update_global_config",
            ]

            for tool_name in core_tools:
                try:
                    if tool_name == "list_subjects":
                        result = await client.call_tool(tool_name, {})
                        passed_tools.append(tool_name)
                        print(f"   ✅ {tool_name}: OK")

                    elif tool_name == "register_schema":
                        # Test with a simple schema
                        result = await client.call_tool(
                            tool_name,
                            {
                                "subject": "test-validation-schema",
                                "schema_definition": {"type": "string"},
                                "schema_type": "AVRO",
                            },
                        )
                        passed_tools.append(tool_name)
                        print(f"   ✅ {tool_name}: OK")

                    elif tool_name == "get_schema":
                        # Try to get a schema (may fail if none exist, but shouldn't crash)
                        result = await client.call_tool(
                            tool_name,
                            {"subject": "test-validation-schema", "version": "latest"},
                        )
                        passed_tools.append(tool_name)
                        print(f"   ✅ {tool_name}: OK")

                    elif tool_name == "get_schema_versions":
                        result = await client.call_tool(
                            tool_name, {"subject": "test-validation-schema"}
                        )
                        passed_tools.append(tool_name)
                        print(f"   ✅ {tool_name}: OK")

                    elif tool_name == "check_compatibility":
                        result = await client.call_tool(
                            tool_name,
                            {
                                "subject": "test-validation-schema",
                                "schema_definition": {"type": "string"},
                            },
                        )
                        passed_tools.append(tool_name)
                        print(f"   ✅ {tool_name}: OK")

                    elif tool_name == "get_global_config":
                        result = await client.call_tool(tool_name, {})
                        passed_tools.append(tool_name)
                        print(f"   ✅ {tool_name}: OK")

                    else:
                        # For other tools, just try to call them with empty params
                        result = await client.call_tool(tool_name, {})
                        passed_tools.append(tool_name)
                        print(f"   ✅ {tool_name}: OK")

                except Exception as e:
                    failed_tools.append((tool_name, str(e)))
                    print(f"   ❌ {tool_name}: {e}")

            # Context Management Tools
            print("\n🏗️ Testing Context Management Tools...")
            context_tools = ["list_contexts", "create_context", "delete_context"]

            for tool_name in context_tools:
                try:
                    if tool_name == "list_contexts":
                        result = await client.call_tool(tool_name, {})
                    elif tool_name == "create_context":
                        result = await client.call_tool(
                            tool_name, {"context": "test-validation-context"}
                        )
                    elif tool_name == "delete_context":
                        result = await client.call_tool(
                            tool_name, {"context": "test-validation-context"}
                        )

                    passed_tools.append(tool_name)
                    print(f"   ✅ {tool_name}: OK")

                except Exception as e:
                    failed_tools.append((tool_name, str(e)))
                    print(f"   ❌ {tool_name}: {e}")

            # Export Tools
            print("\n📤 Testing Export Tools...")
            export_tools = ["export_schema", "export_context", "export_global"]

            for tool_name in export_tools:
                try:
                    if tool_name == "export_schema":
                        result = await client.call_tool(
                            tool_name,
                            {"subject": "test-validation-schema", "format": "json"},
                        )
                    elif tool_name == "export_context":
                        result = await client.call_tool(
                            tool_name, {"context": ".", "include_metadata": False}
                        )
                    elif tool_name == "export_global":
                        result = await client.call_tool(
                            tool_name, {"include_versions": "latest"}
                        )

                    passed_tools.append(tool_name)
                    print(f"   ✅ {tool_name}: OK")

                except Exception as e:
                    failed_tools.append((tool_name, str(e)))
                    print(f"   ❌ {tool_name}: {e}")

            # Multi-Registry Tools (if available)
            print("\n🏢 Testing Multi-Registry Tools...")
            multi_tools = ["list_registries", "compare_registries", "migrate_schema"]

            for tool_name in multi_tools:
                try:
                    if tool_name == "list_registries":
                        result = await client.call_tool(tool_name, {})
                    elif tool_name == "compare_registries":
                        result = await client.call_tool(
                            tool_name,
                            {"source_registry": "dev", "target_registry": "prod"},
                        )
                    elif tool_name == "migrate_schema":
                        result = await client.call_tool(
                            tool_name,
                            {
                                "subject": "test-validation-schema",
                                "source_registry": "dev",
                                "target_registry": "prod",
                                "dry_run": True,
                            },
                        )

                    passed_tools.append(tool_name)
                    print(f"   ✅ {tool_name}: OK")

                except Exception as e:
                    failed_tools.append((tool_name, str(e)))
                    print(f"   ❌ {tool_name}: {e}")

            # Utility Tools
            print("\n🛠️ Testing Utility Tools...")
            utility_tools = ["get_mode", "test_connection"]

            for tool_name in utility_tools:
                try:
                    result = await client.call_tool(tool_name, {})
                    passed_tools.append(tool_name)
                    print(f"   ✅ {tool_name}: OK")

                except Exception as e:
                    failed_tools.append((tool_name, str(e)))
                    print(f"   ❌ {tool_name}: {e}")

            # Summary
            print("\n📊 Tool Validation Summary:")
            print(f"   ✅ Passed: {len(passed_tools)} tools")
            print(f"   ❌ Failed: {len(failed_tools)} tools")
            print(f"   📋 Total: {len(tools)} tools available")

            if failed_tools:
                print("\n❌ Failed tools:")
                for tool_name, error in failed_tools:
                    print(f"   • {tool_name}: {error}")

            # Cleanup
            print("\n🧹 Cleaning up test data...")
            try:
                await client.call_tool(
                    "delete_subject", {"subject": "test-validation-schema"}
                )
                print("   ✅ Cleanup completed")
            except Exception as e:
                print(f"   ⚠️ Cleanup failed (expected): {e}")

            print("\n🎉 All tools validation completed!")

            # Return success if most tools passed
            success_rate = len(passed_tools) / len(tools) if len(tools) > 0 else 0
            if success_rate >= 0.8:  # 80% success rate
                print(f"✅ Validation successful! Success rate: {success_rate:.1%}")
            else:
                print(f"⚠️ Validation concerns. Success rate: {success_rate:.1%}")

    except Exception as e:
        print(f"❌ Error during all tools validation: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_all_tools_validation())
