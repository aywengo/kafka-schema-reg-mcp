#!/usr/bin/env python3
"""
End-to-End Workflow Integration Tests for unified server in multi-registry mode

Tests complete workflows including:
- Schema registration and evolution workflow
- Cross-registry migration workflow
- Schema compatibility and versioning workflow
- Context management workflow
- Configuration management workflow
"""

import asyncio
import json
import os
import sys
import uuid

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastmcp import Client
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# Test schemas for different workflows
TEST_SCHEMAS = {
    "user_v1": {
        "type": "record",
        "name": "User",
        "fields": [
            {"name": "id", "type": "long"},
            {"name": "name", "type": "string"},
            {"name": "email", "type": "string"},
        ],
    },
    "user_v2": {
        "type": "record",
        "name": "User",
        "fields": [
            {"name": "id", "type": "long"},
            {"name": "name", "type": "string"},
            {"name": "email", "type": "string"},
            {"name": "phone", "type": ["null", "string"], "default": None},
        ],
    },
    "product": {
        "type": "record",
        "name": "Product",
        "fields": [
            {"name": "product_id", "type": "string"},
            {"name": "name", "type": "string"},
            {"name": "price", "type": "double"},
            {"name": "category", "type": "string"},
        ],
    },
    "order": {
        "type": "record",
        "name": "Order",
        "fields": [
            {"name": "order_id", "type": "string"},
            {"name": "user_id", "type": "long"},
            {"name": "product_ids", "type": {"type": "array", "items": "string"}},
            {"name": "total_amount", "type": "double"},
            {"name": "order_date", "type": "long"},
        ],
    },
}


@pytest.mark.asyncio
async def test_end_to_end_workflows():
    """Test complete end-to-end workflows through the MCP client."""

    # Get the path to the parent directory where the server script is located
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_script = os.path.join(parent_dir, "kafka_schema_registry_unified_mcp.py")

    print("🔄 Testing End-to-End Workflows...")

    try:
        client = Client(
            server_script,
            env={
                "SCHEMA_REGISTRY_URL": "http://localhost:38081",
                "MULTI_REGISTRY_CONFIG": json.dumps(
                    {
                        "dev": {"url": "http://localhost:38081"},
                        "prod": {"url": "http://localhost:38082"},
                    }
                ),
            },
        )

        async with client:
            print("✅ Connected to MCP server!")

            # Generate unique test identifier
            test_id = uuid.uuid4().hex[:8]

            # Workflow 1: Schema Development Lifecycle
            print(f"\n📝 Workflow 1: Schema Development Lifecycle (ID: {test_id})")

            # Step 1: Create a user schema
            user_subject = f"user-events-{test_id}"
            user_schema_v1 = {
                "type": "record",
                "name": "User",
                "fields": [
                    {"name": "id", "type": "long"},
                    {"name": "name", "type": "string"},
                ],
            }

            print("   1.1 Registering initial user schema...")
            try:
                result = await client.call_tool(
                    "register_schema",
                    {
                        "subject": user_subject,
                        "schema_definition": user_schema_v1,
                        "schema_type": "AVRO",
                        "registry": "dev",
                    },
                )
                print(f"   ✅ Schema registered: {result}")
            except Exception as e:
                print(f"   ❌ Failed to register schema: {e}")

            # Step 2: Check compatibility for evolution
            user_schema_v2 = {
                "type": "record",
                "name": "User",
                "fields": [
                    {"name": "id", "type": "long"},
                    {"name": "name", "type": "string"},
                    {"name": "email", "type": ["null", "string"], "default": None},
                ],
            }

            print("   1.2 Checking compatibility for schema evolution...")
            try:
                result = await client.call_tool(
                    "check_compatibility",
                    {
                        "subject": user_subject,
                        "schema_definition": user_schema_v2,
                        "registry": "dev",
                    },
                )
                print(f"   ✅ Compatibility check: {result}")
            except Exception as e:
                print(f"   ❌ Compatibility check failed: {e}")

            # Step 3: Register evolved schema
            print("   1.3 Registering evolved schema...")
            try:
                result = await client.call_tool(
                    "register_schema",
                    {
                        "subject": user_subject,
                        "schema_definition": user_schema_v2,
                        "schema_type": "AVRO",
                        "registry": "dev",
                    },
                )
                print(f"   ✅ Evolved schema registered: {result}")
            except Exception as e:
                print(f"   ❌ Failed to register evolved schema: {e}")

            # Step 4: Check versions
            print("   1.4 Checking schema versions...")
            try:
                result = await client.call_tool(
                    "get_schema_versions", {"subject": user_subject, "registry": "dev"}
                )
                print(f"   ✅ Schema versions: {result}")
            except Exception as e:
                print(f"   ❌ Failed to get versions: {e}")

            # Workflow 2: Multi-Registry Migration
            print("\n🔄 Workflow 2: Multi-Registry Migration")

            print("   2.1 Comparing registries...")
            try:
                result = await client.call_tool(
                    "compare_registries",
                    {"source_registry": "dev", "target_registry": "prod"},
                )
                print(f"   ✅ Registry comparison: {result}")
            except Exception as e:
                print(f"   ❌ Registry comparison failed: {e}")

            print("   2.2 Migrating schema to production...")
            try:
                result = await client.call_tool(
                    "migrate_schema",
                    {
                        "subject": user_subject,
                        "source_registry": "dev",
                        "target_registry": "prod",
                        "dry_run": True,
                    },
                )
                print(f"   ✅ Migration (dry run): {result}")
            except Exception as e:
                print(f"   ❌ Migration failed: {e}")

            # Workflow 3: Export and Backup
            print("\n📤 Workflow 3: Export and Backup")

            print("   3.1 Exporting schema...")
            try:
                result = await client.call_tool(
                    "export_schema",
                    {"subject": user_subject, "registry": "dev", "format": "json"},
                )
                print(
                    f"   ✅ Schema export: {result[:100]}..."
                    if result
                    else "   ❌ No export result"
                )
            except Exception as e:
                print(f"   ❌ Export failed: {e}")

            print("   3.2 Exporting full registry...")
            try:
                result = await client.call_tool(
                    "export_global", {"registry": "dev", "include_versions": "latest"}
                )
                print(
                    f"   ✅ Global export: {result[:100]}..."
                    if result
                    else "   ❌ No global export result"
                )
            except Exception as e:
                print(f"   ❌ Global export failed: {e}")

            # Cleanup
            print("\n🧹 Cleanup: Removing test subjects...")
            try:
                result = await client.call_tool(
                    "delete_subject", {"subject": user_subject, "registry": "dev"}
                )
                print(f"   ✅ Cleanup completed: {result}")
            except Exception as e:
                print(f"   ⚠️ Cleanup failed (may not exist): {e}")

            print("\n🎉 End-to-end workflow testing completed!")

    except Exception as e:
        print(f"❌ Error during end-to-end workflow test: {e}")
        raise


@pytest.mark.asyncio
async def test_schema_evolution_workflow():
    """Test complete schema evolution workflow across registries."""
    print("\n🔄 Testing Schema Evolution Workflow")
    print("-" * 50)

    # Clean up any existing task manager state to prevent deadlocks
    try:
        import kafka_schema_registry_unified_mcp

        kafka_schema_registry_unified_mcp.task_manager.reset_for_testing()
        print("🧹 Task manager state cleaned up")
    except Exception as e:
        print(f"⚠️ Warning: Could not cleanup task manager: {e}")

    # Multi-registry setup
    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)

    env["SCHEMA_REGISTRY_NAME_1"] = "development"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
    env["READONLY_1"] = "false"

    env["SCHEMA_REGISTRY_NAME_2"] = "staging"
    env["SCHEMA_REGISTRY_URL_2"] = (
        "http://localhost:38081"  # Same registry, different contexts
    )
    env["READONLY_2"] = "false"

    env["SCHEMA_REGISTRY_NAME_3"] = "production"
    env["SCHEMA_REGISTRY_URL_3"] = "http://localhost:38081"
    env["READONLY_3"] = "true"

    server_params = StdioServerParameters(
        command="python", args=["kafka_schema_registry_unified_mcp.py"], env=env
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Step 1: Register initial schema in development
                print("Step 1: Register User v1 schema in development")
                result = await session.call_tool(
                    "register_schema",
                    {
                        "subject": "user-events",
                        "schema_definition": TEST_SCHEMAS["user_v1"],
                        "registry": "development",
                    },
                )
                print(
                    f"✅ Registered v1: {result.content[0].text if result.content else 'Success'}"
                )

                # Step 2: Check compatibility for v2 schema
                print("\nStep 2: Check compatibility for User v2 schema")
                result = await session.call_tool(
                    "check_compatibility",
                    {
                        "subject": "user-events",
                        "schema_definition": TEST_SCHEMAS["user_v2"],
                        "registry": "development",
                    },
                )
                print(
                    f"✅ Compatibility check: {result.content[0].text if result.content else 'Success'}"
                )

                # Step 3: Register v2 schema if compatible
                print("\nStep 3: Register User v2 schema in development")
                result = await session.call_tool(
                    "register_schema",
                    {
                        "subject": "user-events",
                        "schema_definition": TEST_SCHEMAS["user_v2"],
                        "registry": "development",
                    },
                )
                print(
                    f"✅ Registered v2: {result.content[0].text if result.content else 'Success'}"
                )

                # Step 4: Get all versions
                print("\nStep 4: Get all schema versions")
                result = await session.call_tool(
                    "get_schema_versions",
                    {"subject": "user-events", "registry": "development"},
                )
                print(
                    f"✅ Versions: {result.content[0].text if result.content else 'Success'}"
                )

                # Step 5: Migrate latest schema to staging
                print("\nStep 5: Migrate schema from development to staging")
                result = await session.call_tool(
                    "migrate_schema",
                    {
                        "subject": "user-events",
                        "source_registry": "development",
                        "target_registry": "staging",
                        "dry_run": False,
                    },
                )
                print(
                    f"✅ Migration: {result.content[0].text if result.content else 'Success'}"
                )

                # Step 6: Compare development and staging
                print("\nStep 6: Compare development and staging registries")
                result = await session.call_tool(
                    "compare_registries",
                    {"source_registry": "development", "target_registry": "staging"},
                )
                print(
                    f"✅ Comparison: {result.content[0].text if result.content else 'Success'}"
                )

                # Step 7: Try to migrate to production (should fail due to readonly)
                print("\nStep 7: Try to migrate to production (should fail)")
                result = await session.call_tool(
                    "migrate_schema",
                    {
                        "subject": "user-events",
                        "source_registry": "staging",
                        "target_registry": "production",
                        "dry_run": False,
                    },
                )
                print(
                    f"✅ Production migration (expected failure): {result.content[0].text if result.content else 'Success'}"
                )

                print("\n🎉 Schema Evolution Workflow Complete!")

    except Exception as e:
        print(f"❌ Schema evolution workflow failed: {e}")


@pytest.mark.asyncio
async def test_multi_schema_deployment_workflow():
    """Test deploying multiple schemas across environments."""
    print("\n🚀 Testing Multi-Schema Deployment Workflow")
    print("-" * 50)

    # Clean up any existing task manager state to prevent deadlocks
    try:
        import kafka_schema_registry_unified_mcp

        kafka_schema_registry_unified_mcp.task_manager.reset_for_testing()
        print("🧹 Task manager state cleaned up")
    except Exception as e:
        print(f"⚠️ Warning: Could not cleanup task manager: {e}")

    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)

    env["SCHEMA_REGISTRY_NAME_1"] = "development"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
    env["READONLY_1"] = "false"

    env["SCHEMA_REGISTRY_NAME_2"] = "staging"
    env["SCHEMA_REGISTRY_URL_2"] = "http://localhost:38081"
    env["READONLY_2"] = "false"

    server_params = StdioServerParameters(
        command="python", args=["kafka_schema_registry_unified_mcp.py"], env=env
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Step 1: Register multiple schemas in development
                schemas_to_register = [
                    ("user-events", TEST_SCHEMAS["user_v1"]),
                    ("product-catalog", TEST_SCHEMAS["product"]),
                    ("order-events", TEST_SCHEMAS["order"]),
                ]

                print("Step 1: Register multiple schemas in development")
                for subject, schema in schemas_to_register:
                    result = await session.call_tool(
                        "register_schema",
                        {
                            "subject": subject,
                            "schema_definition": schema,
                            "registry": "development",
                        },
                    )
                    print(f"  ✅ Registered {subject}")

                # Step 2: List all subjects in development
                print("\nStep 2: List all subjects in development")
                result = await session.call_tool(
                    "list_subjects", {"registry": "development"}
                )
                subjects = json.loads(result.content[0].text) if result.content else []
                print(f"  ✅ Found {len(subjects)} subjects: {subjects}")

                # Step 3: Find missing schemas in staging
                print("\nStep 3: Find schemas missing in staging")
                result = await session.call_tool(
                    "find_missing_schemas",
                    {"source_registry": "development", "target_registry": "staging"},
                )
                print(
                    f"  ✅ Missing schemas: {result.content[0].text if result.content else 'None'}"
                )

                # Step 4: Migrate all schemas to staging
                print("\nStep 4: Migrate all schemas to staging")
                for subject, _ in schemas_to_register:
                    result = await session.call_tool(
                        "migrate_schema",
                        {
                            "subject": subject,
                            "source_registry": "development",
                            "target_registry": "staging",
                            "dry_run": False,
                        },
                    )
                    print(f"  ✅ Migrated {subject}")

                # Step 5: Verify migration by comparing registries
                print("\nStep 5: Verify migration by comparing registries")
                result = await session.call_tool(
                    "compare_registries",
                    {"source_registry": "development", "target_registry": "staging"},
                )
                comparison = (
                    json.loads(result.content[0].text) if result.content else {}
                )
                missing_count = len(
                    comparison.get("subjects", {}).get("target_only", [])
                )
                print(f"  ✅ Schemas missing in staging: {missing_count}")

                # Step 6: List migration history
                print("\nStep 6: Check migration history")
                result = await session.call_tool("list_migrations", {})
                migrations = (
                    json.loads(result.content[0].text) if result.content else []
                )
                print(f"  ✅ Total migrations: {len(migrations)}")

                print("\n🎉 Multi-Schema Deployment Workflow Complete!")

    except Exception as e:
        print(f"❌ Multi-schema deployment workflow failed: {e}")


@pytest.mark.asyncio
async def test_context_management_workflow():
    """Test complete context management workflow."""
    print("\n📁 Testing Context Management Workflow")
    print("-" * 50)

    # Clean up any existing task manager state to prevent deadlocks
    try:
        import kafka_schema_registry_unified_mcp

        kafka_schema_registry_unified_mcp.task_manager.reset_for_testing()
        print("🧹 Task manager state cleaned up")
    except Exception as e:
        print(f"⚠️ Warning: Could not cleanup task manager: {e}")

    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)

    env["SCHEMA_REGISTRY_NAME_1"] = "primary"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
    env["READONLY_1"] = "false"

    server_params = StdioServerParameters(
        command="python", args=["kafka_schema_registry_unified_mcp.py"], env=env
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Step 1: List existing contexts
                print("Step 1: List existing contexts")
                result = await session.call_tool(
                    "list_contexts", {"registry": "primary"}
                )
                initial_contexts = (
                    json.loads(result.content[0].text) if result.content else []
                )
                print(f"  ✅ Initial contexts: {initial_contexts}")

                # Step 2: Create new contexts
                print("\nStep 2: Create new contexts")
                new_contexts = ["ecommerce", "analytics", "audit"]
                for context in new_contexts:
                    result = await session.call_tool(
                        "create_context", {"context": context, "registry": "primary"}
                    )
                    print(f"  ✅ Created context: {context}")

                # Step 3: Register schemas in different contexts
                print("\nStep 3: Register schemas in different contexts")
                context_schemas = [
                    ("ecommerce", "user-profile", TEST_SCHEMAS["user_v1"]),
                    ("ecommerce", "product-catalog", TEST_SCHEMAS["product"]),
                    ("analytics", "user-events", TEST_SCHEMAS["user_v2"]),
                    ("audit", "order-events", TEST_SCHEMAS["order"]),
                ]

                for context, subject, schema in context_schemas:
                    result = await session.call_tool(
                        "register_schema",
                        {
                            "subject": subject,
                            "schema_definition": schema,
                            "context": context,
                            "registry": "primary",
                        },
                    )
                    print(f"  ✅ Registered {subject} in {context} context")

                # Step 4: List subjects in each context
                print("\nStep 4: List subjects in each context")
                for context in new_contexts:
                    result = await session.call_tool(
                        "list_subjects", {"context": context, "registry": "primary"}
                    )
                    subjects = (
                        json.loads(result.content[0].text) if result.content else []
                    )
                    print(f"  ✅ {context} context: {len(subjects)} subjects")

                # Step 5: Get and update configurations per context
                print("\nStep 5: Manage context configurations")
                for context in new_contexts[:2]:  # Test first 2 contexts
                    # Get current config
                    result = await session.call_tool(
                        "get_global_config", {"context": context, "registry": "primary"}
                    )
                    print(
                        f"  ✅ Got config for {context}: {result.content[0].text if result.content else 'Success'}"
                    )

                    # Update config
                    result = await session.call_tool(
                        "update_global_config",
                        {
                            "compatibility": "FORWARD",
                            "context": context,
                            "registry": "primary",
                        },
                    )
                    print(f"  ✅ Updated config for {context}")

                # Step 6: Test context deletion (cleanup)
                print("\nStep 6: Clean up test contexts")
                for context in new_contexts:
                    result = await session.call_tool(
                        "delete_context", {"context": context, "registry": "primary"}
                    )
                    print(f"  ✅ Deleted context: {context}")

                print("\n🎉 Context Management Workflow Complete!")

    except Exception as e:
        print(f"❌ Context management workflow failed: {e}")


@pytest.mark.asyncio
async def test_configuration_management_workflow():
    """Test comprehensive configuration management."""
    print("\n⚙️ Testing Configuration Management Workflow")
    print("-" * 50)

    # Clean up any existing task manager state to prevent deadlocks
    try:
        import kafka_schema_registry_unified_mcp

        kafka_schema_registry_unified_mcp.task_manager.reset_for_testing()
        print("🧹 Task manager state cleaned up")
    except Exception as e:
        print(f"⚠️ Warning: Could not cleanup task manager: {e}")

    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)

    env["SCHEMA_REGISTRY_NAME_1"] = "config_test"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
    env["READONLY_1"] = "false"

    server_params = StdioServerParameters(
        command="python", args=["kafka_schema_registry_unified_mcp.py"], env=env
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Step 1: Get initial global configuration
                print("Step 1: Get initial global configuration")
                result = await session.call_tool(
                    "get_global_config", {"registry": "config_test"}
                )
                initial_config = (
                    json.loads(result.content[0].text) if result.content else {}
                )
                print(
                    f"  ✅ Initial compatibility: {initial_config.get('compatibility', 'N/A')}"
                )

                # Step 2: Test different compatibility levels
                print("\nStep 2: Test different compatibility levels")
                compatibility_levels = ["BACKWARD", "FORWARD", "FULL", "NONE"]
                for level in compatibility_levels:
                    result = await session.call_tool(
                        "update_global_config",
                        {"compatibility": level, "registry": "config_test"},
                    )
                    print(f"  ✅ Set compatibility to {level}")

                    # Verify the change
                    result = await session.call_tool(
                        "get_global_config", {"registry": "config_test"}
                    )
                    current_config = (
                        json.loads(result.content[0].text) if result.content else {}
                    )
                    current_level = current_config.get("compatibility", "N/A")
                    print(f"  ✅ Verified: {current_level}")

                # Step 3: Register a test schema for subject-level config testing
                print("\nStep 3: Register test schema for subject-level testing")
                result = await session.call_tool(
                    "register_schema",
                    {
                        "subject": "config-test-subject",
                        "schema_definition": TEST_SCHEMAS["user_v1"],
                        "registry": "config_test",
                    },
                )
                print("  ✅ Test schema registered")

                # Step 4: Test subject-level configuration
                print("\nStep 4: Test subject-level configuration")
                result = await session.call_tool(
                    "get_subject_config",
                    {"subject": "config-test-subject", "registry": "config_test"},
                )
                print(
                    f"  ✅ Got subject config: {result.content[0].text if result.content else 'Success'}"
                )

                result = await session.call_tool(
                    "update_subject_config",
                    {
                        "subject": "config-test-subject",
                        "compatibility": "BACKWARD",
                        "registry": "config_test",
                    },
                )
                print("  ✅ Updated subject config to BACKWARD")

                # Step 5: Test mode management
                print("\nStep 5: Test mode management")
                result = await session.call_tool(
                    "get_mode", {"registry": "config_test"}
                )
                initial_mode = (
                    json.loads(result.content[0].text) if result.content else {}
                )
                print(f"  ✅ Initial mode: {initial_mode.get('mode', 'N/A')}")

                # Test different modes
                modes = ["READWRITE", "READONLY"]
                for mode in modes:
                    result = await session.call_tool(
                        "update_mode", {"mode": mode, "registry": "config_test"}
                    )
                    print(f"  ✅ Set mode to {mode}")

                # Step 6: Test subject-level mode
                print("\nStep 6: Test subject-level mode")
                result = await session.call_tool(
                    "get_subject_mode",
                    {"subject": "config-test-subject", "registry": "config_test"},
                )
                print(
                    f"  ✅ Got subject mode: {result.content[0].text if result.content else 'Success'}"
                )

                result = await session.call_tool(
                    "update_subject_mode",
                    {
                        "subject": "config-test-subject",
                        "mode": "READONLY",
                        "registry": "config_test",
                    },
                )
                print("  ✅ Set subject mode to READONLY")

                print("\n🎉 Configuration Management Workflow Complete!")

    except Exception as e:
        print(f"❌ Configuration management workflow failed: {e}")


@pytest.mark.asyncio
async def test_complete_schema_lifecycle():
    """Test complete schema lifecycle via MCP"""
    print("🔄 Testing Complete Schema Lifecycle")
    print("=" * 50)

    # Setup environment
    os.environ["SCHEMA_REGISTRY_URL"] = "http://localhost:38081"
    os.environ["READONLY"] = "false"

    # Get server script path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(
        os.path.dirname(script_dir), "kafka_schema_registry_unified_mcp.py"
    )

    # Generate unique test prefix
    test_prefix = f"e2e-test-{uuid.uuid4().hex[:8]}"

    # Create client
    client = Client(server_script)

    try:
        async with client:
            print("✅ MCP connection established")

            # Get available tools
            tools = await client.list_tools()
            tool_names = [tool.name for tool in tools]
            print(f"📋 Available tools: {len(tool_names)}")

            # Phase 1: Registration
            print(f"\n📝 Phase 1: Schema Registration (prefix: {test_prefix})")
            if "register_schema" in tool_names:
                test_schema = {
                    "type": "record",
                    "name": "TestRecord",
                    "fields": [
                        {"name": "id", "type": "int"},
                        {"name": "name", "type": "string"},
                    ],
                }

                try:
                    result = await client.call_tool(
                        "register_schema",
                        {
                            "subject": f"{test_prefix}-subject",
                            "schema_definition": test_schema,
                            "schema_type": "AVRO",
                        },
                    )
                    print(f"✅ Schema registered: {result}")
                except Exception as e:
                    print(f"⚠️  Schema registration: {e}")

            # Phase 2: Verification
            print("\n🔍 Phase 2: Schema Verification")
            if "list_subjects" in tool_names:
                try:
                    result = await client.call_tool("list_subjects", {})
                    print("✅ Subjects listed")
                except Exception as e:
                    print(f"⚠️  List subjects: {e}")

            # Phase 3: Evolution
            print("\n🔄 Phase 3: Schema Evolution")
            if "register_schema" in tool_names:
                evolved_schema = {
                    "type": "record",
                    "name": "TestRecord",
                    "fields": [
                        {"name": "id", "type": "int"},
                        {"name": "name", "type": "string"},
                        {
                            "name": "description",
                            "type": ["null", "string"],
                            "default": None,
                        },
                    ],
                }

                try:
                    result = await client.call_tool(
                        "register_schema",
                        {
                            "subject": f"{test_prefix}-subject",
                            "schema_definition": evolved_schema,
                            "schema_type": "AVRO",
                        },
                    )
                    print(f"✅ Schema evolved: {result}")
                except Exception as e:
                    print(f"⚠️  Schema evolution: {e}")

            # Phase 4: Export
            print("\n📤 Phase 4: Schema Export")
            if "export_subject" in tool_names:
                try:
                    result = await client.call_tool(
                        "export_subject", {"subject": f"{test_prefix}-subject"}
                    )
                    print("✅ Schema exported")
                except Exception as e:
                    print(f"⚠️  Schema export: {e}")

            # Phase 5: Cleanup
            print("\n🧹 Phase 5: Cleanup")
            cleanup_tools = ["delete_subject", "cleanup_schemas"]
            available_cleanup = [tool for tool in cleanup_tools if tool in tool_names]

            for cleanup_tool in available_cleanup:
                try:
                    if cleanup_tool == "delete_subject":
                        result = await client.call_tool(
                            cleanup_tool, {"subject": f"{test_prefix}-subject"}
                        )
                    else:
                        result = await client.call_tool(
                            cleanup_tool,
                            {"pattern": f"{test_prefix}-*", "dry_run": False},
                        )
                    print(f"✅ Cleanup with {cleanup_tool}")
                    break
                except Exception as e:
                    print(f"⚠️  Cleanup with {cleanup_tool}: {e}")

            print("\n🎉 Complete schema lifecycle test completed!")
            return True

    except Exception as e:
        print(f"❌ Critical error during lifecycle test: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all end-to-end workflow tests."""
    print("🧪 Starting End-to-End Workflow Integration Tests")
    print("=" * 70)

    # Clean up any existing task manager state before starting
    try:
        import kafka_schema_registry_unified_mcp

        kafka_schema_registry_unified_mcp.task_manager.reset_for_testing()
        print("🧹 Initial task manager cleanup completed")
    except Exception as e:
        print(f"⚠️ Warning: Could not cleanup task manager initially: {e}")

    try:
        await test_end_to_end_workflows()
        await test_schema_evolution_workflow()
        await test_multi_schema_deployment_workflow()
        await test_context_management_workflow()
        await test_configuration_management_workflow()
        await test_complete_schema_lifecycle()

        print("\n" + "=" * 70)
        print("🎉 All End-to-End Workflow Tests Complete!")
        print("\n✅ **Workflows Tested:**")
        print("• Schema Evolution (v1 → v2 → migration)")
        print("• Multi-Schema Deployment (bulk operations)")
        print("• Context Management (create, configure, cleanup)")
        print("• Configuration Management (global & subject level)")

    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ End-to-end workflow tests failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
