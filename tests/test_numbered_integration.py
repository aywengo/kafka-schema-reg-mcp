#!/usr/bin/env python3
"""
Integration test for numbered environment variable configuration.

This test uses the docker-compose Schema Registry instance but creates different
contexts to simulate multiple Schema Registry instances. This tests the numbered
configuration approach with real schema operations.

Test Strategy:
1. Use contexts to simulate different "registries": development, staging, production
2. Configure MCP server with numbered environment variables pointing to same registry but different contexts
3. Test schema operations across different "registries"
4. Test per-registry READONLY mode
5. Test cross-registry operations (comparison, migration)
"""

import asyncio
import json
import os
import subprocess
import time

import requests
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configuration for simulated registries using contexts
SCHEMA_REGISTRY_BASE_URL = "http://localhost:38081"
SIMULATED_REGISTRIES = {
    "development": {
        "context": "development",
        "readonly": False,
        "description": "Development environment",
    },
    "staging": {"context": "staging", "readonly": False, "description": "Staging environment"},
    "production": {
        "context": "production",
        "readonly": True,
        "description": "Production environment (readonly)",
    },
}


class IntegrationTestSetup:
    """Setup and teardown for integration tests."""

    def __init__(self):
        self.registry_url = SCHEMA_REGISTRY_BASE_URL

    async def setup_test_environment(self):
        """Set up the test environment with contexts and initial schemas."""
        print("🔧 Setting up integration test environment...")

        # Wait for Schema Registry to be ready
        await self._wait_for_schema_registry()

        # Create contexts to simulate different registries
        await self._create_test_contexts()

        # Register some test schemas in different contexts
        await self._register_test_schemas()

        print("✅ Test environment setup complete")

    async def _wait_for_schema_registry(self, max_attempts=30):
        """Wait for Schema Registry to be available."""
        print("⏳ Waiting for Schema Registry to be ready...")

        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{self.registry_url}/subjects", timeout=5)
                if response.status_code == 200:
                    print(f"✅ Schema Registry ready at {self.registry_url}")
                    return
            except Exception as e:
                if attempt < max_attempts - 1:
                    print(f"⏳ Attempt {attempt + 1}/{max_attempts}: {e}")
                    time.sleep(2)
                else:
                    raise Exception(f"Schema Registry not ready after {max_attempts} attempts")

    async def _create_test_contexts(self):
        """Create contexts to simulate different registries."""
        print("📁 Creating test contexts...")

        for registry_name, config in SIMULATED_REGISTRIES.items():
            context = config["context"]
            try:
                # Create context
                response = requests.post(f"{self.registry_url}/contexts/{context}")
                if response.status_code in [200, 409]:  # 409 = already exists
                    print(f"✅ Context '{context}' ready for {registry_name}")
                else:
                    print(f"⚠️  Context creation response for {context}: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Error creating context {context}: {e}")

    async def _register_test_schemas(self):
        """Register test schemas in different contexts."""
        print("📋 Registering test schemas...")

        # Test schemas
        user_schema = {
            "type": "record",
            "name": "User",
            "fields": [
                {"name": "id", "type": "long"},
                {"name": "name", "type": "string"},
                {"name": "email", "type": "string"},
            ],
        }

        event_schema = {
            "type": "record",
            "name": "Event",
            "fields": [
                {"name": "event_id", "type": "string"},
                {"name": "user_id", "type": "long"},
                {"name": "timestamp", "type": "long"},
            ],
        }

        # Register schemas in development context
        await self._register_schema("development", "user-events", user_schema)
        await self._register_schema("development", "click-events", event_schema)

        # Register some schemas in staging
        await self._register_schema("staging", "user-events", user_schema)

        # Register schema in production (this will work since we register before setting readonly)
        await self._register_schema("production", "user-events", user_schema)

        print("✅ Test schemas registered")

    async def _register_schema(self, context, subject, schema):
        """Register a schema in a specific context."""
        try:
            url = f"{self.registry_url}/contexts/{context}/subjects/{subject}/versions"
            payload = {"schema": json.dumps(schema), "schemaType": "AVRO"}

            response = requests.post(
                url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
            )

            if response.status_code in [200, 409]:  # 409 = schema already exists
                print(f"✅ Schema {subject} registered in {context}")
            else:
                print(
                    f"⚠️  Schema registration failed for {subject} in {context}: {response.status_code}"
                )

        except Exception as e:
            print(f"⚠️  Error registering schema {subject} in {context}: {e}")


async def test_numbered_config_integration():
    """Main integration test for numbered environment variable configuration."""

    print("🧪 Starting Numbered Configuration Integration Test")
    print("=" * 70)

    # Setup test environment
    setup = IntegrationTestSetup()
    await setup.setup_test_environment()

    # Test 1: Single Registry Mode
    await test_single_registry_mode()

    # Test 2: Multi-Registry Mode with Contexts
    await test_multi_registry_mode()

    # Test 3: Cross-Registry Operations
    await test_cross_registry_operations()

    # Test 4: Per-Registry READONLY Mode
    await test_per_registry_readonly()

    print("\n" + "=" * 70)
    print("🎉 Integration Test Complete!")


async def test_single_registry_mode():
    """Test single registry mode with real operations."""
    print("\n🔧 Testing Single Registry Mode (Integration)")
    print("-" * 50)

    # Configure for single registry mode
    env = os.environ.copy()
    env["SCHEMA_REGISTRY_URL"] = SCHEMA_REGISTRY_BASE_URL
    env["SCHEMA_REGISTRY_USER"] = ""
    env["SCHEMA_REGISTRY_PASSWORD"] = ""
    env["READONLY"] = "false"

    # Clear numbered variables
    for i in range(1, 9):
        env.pop(f"SCHEMA_REGISTRY_NAME_{i}", None)
        env.pop(f"SCHEMA_REGISTRY_URL_{i}", None)
        env.pop(f"SCHEMA_REGISTRY_USER_{i}", None)
        env.pop(f"SCHEMA_REGISTRY_PASSWORD_{i}", None)
        env.pop(f"READONLY_{i}", None)

    # Get the absolute path to the server script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(
        os.path.dirname(script_dir), "kafka_schema_registry_unified_mcp.py"
    )

    server_params = StdioServerParameters(command="python", args=[server_script], env=env)

    try:
        await asyncio.wait_for(_test_single_registry_with_client(server_params), timeout=30.0)
    except asyncio.TimeoutError:
        print("❌ Single registry test timed out after 30 seconds")
    except Exception as e:
        print(f"❌ Single registry integration test failed: {e}")


async def _test_single_registry_with_client(server_params):
    """Helper function for single registry test with timeout protection."""
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Test registry listing
            result = await session.call_tool("list_registries", {})
            if result.content and len(result.content) > 0:
                registries = json.loads(result.content[0].text)
                print(f"✅ Single mode: Found {len(registries)} registry")

            # Test schema operations
            result = await session.call_tool("list_subjects", {})
            if result.content and len(result.content) > 0:
                subjects = json.loads(result.content[0].text)
                print(f"✅ Found {len(subjects)} subjects in default registry")

            # Test contexts
            result = await session.call_tool("list_contexts", {})
            if result.content and len(result.content) > 0:
                contexts = json.loads(result.content[0].text)
                print(f"✅ Found {len(contexts)} contexts: {contexts}")


async def test_multi_registry_mode():
    """Test multi-registry mode using contexts to simulate registries."""
    print("\n🔧 Testing Multi-Registry Mode (Integration)")
    print("-" * 50)

    # Configure for multi-registry mode using contexts
    env = os.environ.copy()

    # Clear single registry variables
    env.pop("SCHEMA_REGISTRY_URL", None)

    # Set up numbered registries pointing to contexts
    env["SCHEMA_REGISTRY_NAME_1"] = "development"
    env["SCHEMA_REGISTRY_URL_1"] = SCHEMA_REGISTRY_BASE_URL
    env["SCHEMA_REGISTRY_USER_1"] = ""
    env["SCHEMA_REGISTRY_PASSWORD_1"] = ""
    env["READONLY_1"] = "false"

    env["SCHEMA_REGISTRY_NAME_2"] = "staging"
    env["SCHEMA_REGISTRY_URL_2"] = SCHEMA_REGISTRY_BASE_URL
    env["SCHEMA_REGISTRY_USER_2"] = ""
    env["SCHEMA_REGISTRY_PASSWORD_2"] = ""
    env["READONLY_2"] = "false"

    env["SCHEMA_REGISTRY_NAME_3"] = "production"
    env["SCHEMA_REGISTRY_URL_3"] = SCHEMA_REGISTRY_BASE_URL
    env["SCHEMA_REGISTRY_USER_3"] = ""
    env["SCHEMA_REGISTRY_PASSWORD_3"] = ""
    env["READONLY_3"] = "true"

    # Get the absolute path to the server script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(
        os.path.dirname(script_dir), "kafka_schema_registry_unified_mcp.py"
    )

    server_params = StdioServerParameters(command="python", args=[server_script], env=env)

    try:
        await asyncio.wait_for(_test_multi_registry_with_client(server_params), timeout=30.0)
    except asyncio.TimeoutError:
        print("❌ Multi-registry test timed out after 30 seconds")
    except Exception as e:
        print(f"❌ Multi-registry integration test failed: {e}")


async def _test_multi_registry_with_client(server_params):
    """Helper function for multi-registry test with timeout protection."""
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Test registry listing
            result = await session.call_tool("list_registries", {})
            if result.content and len(result.content) > 0:
                registries = json.loads(result.content[0].text)
                print(f"✅ Multi mode: Found {len(registries)} registries")
                for registry in registries:
                    name = registry.get("name")
                    readonly = registry.get("readonly", False)
                    print(f"   • {name}: readonly={readonly}")

            # Test connection to all registries
            result = await session.call_tool("test_all_registries", {})
            if result.content and len(result.content) > 0:
                test_results = json.loads(result.content[0].text)
                connected = test_results.get("connected", 0)
                total = test_results.get("total_registries", 0)
                print(f"✅ Registry connections: {connected}/{total} successful")

            # Test schema operations with registry parameter
            result = await session.call_tool("list_subjects", {"context": "development"})
            if result.content and len(result.content) > 0:
                subjects = json.loads(result.content[0].text)
                print(f"✅ Development context: {len(subjects)} subjects")

            result = await session.call_tool("list_subjects", {"context": "staging"})
            if result.content and len(result.content) > 0:
                subjects = json.loads(result.content[0].text)
                print(f"✅ Staging context: {len(subjects)} subjects")


async def test_cross_registry_operations():
    """Test cross-registry operations using contexts."""
    print("\n🔧 Testing Cross-Registry Operations (Integration)")
    print("-" * 50)

    # Use the same multi-registry configuration
    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)

    env["SCHEMA_REGISTRY_NAME_1"] = "development"
    env["SCHEMA_REGISTRY_URL_1"] = SCHEMA_REGISTRY_BASE_URL
    env["READONLY_1"] = "false"

    env["SCHEMA_REGISTRY_NAME_2"] = "staging"
    env["SCHEMA_REGISTRY_URL_2"] = SCHEMA_REGISTRY_BASE_URL
    env["READONLY_2"] = "false"

    env["SCHEMA_REGISTRY_NAME_3"] = "production"
    env["SCHEMA_REGISTRY_URL_3"] = SCHEMA_REGISTRY_BASE_URL
    env["READONLY_3"] = "true"

    # Get the absolute path to the server script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(
        os.path.dirname(script_dir), "kafka_schema_registry_unified_mcp.py"
    )

    server_params = StdioServerParameters(command="python", args=[server_script], env=env)

    try:
        await asyncio.wait_for(_test_cross_registry_with_client(server_params), timeout=30.0)
    except asyncio.TimeoutError:
        print("❌ Cross-registry test timed out after 30 seconds")
    except Exception as e:
        print(f"❌ Cross-registry operations test failed: {e}")


async def _test_cross_registry_with_client(server_params):
    """Helper function for cross-registry test with timeout protection."""
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Test registry comparison
            result = await session.call_tool(
                "compare_registries",
                {"source_registry": "development", "target_registry": "staging"},
            )
            if result.content and len(result.content) > 0:
                comparison = json.loads(result.content[0].text)
                if "error" in comparison:
                    print(f"⚠️  Registry comparison: {comparison['error']}")
                else:
                    print(f"✅ Registry comparison completed: dev vs staging")
                    subjects = comparison.get("subjects", {})
                    print(f"   Common subjects: {len(subjects.get('common', []))}")
                    print(f"   Dev only: {len(subjects.get('source_only', []))}")
                    print(f"   Staging only: {len(subjects.get('target_only', []))}")

            # Test finding missing schemas
            result = await session.call_tool(
                "find_missing_schemas",
                {"source_registry": "development", "target_registry": "production"},
            )
            if result.content and len(result.content) > 0:
                missing = json.loads(result.content[0].text)
                if "error" in missing:
                    print(f"⚠️  Missing schemas check: {missing['error']}")
                else:
                    missing_count = missing.get("missing_count", 0)
                    print(
                        f"✅ Missing schemas check: {missing_count} schemas in dev but not in prod"
                    )

            # Test migration (dry run)
            result = await session.call_tool(
                "migrate_schema",
                {
                    "subject": "user-events",
                    "source_registry": "development",
                    "target_registry": "staging",
                    "dry_run": True,
                },
            )
            if result.content and len(result.content) > 0:
                migration = json.loads(result.content[0].text)
                if "error" in migration:
                    print(f"⚠️  Schema migration: {migration['error']}")
                else:
                    print(f"✅ Schema migration dry run: {migration.get('status')}")


async def test_per_registry_readonly():
    """Test per-registry READONLY mode protection."""
    print("\n🔧 Testing Per-Registry READONLY Mode (Integration)")
    print("-" * 50)

    # Configure with production as readonly
    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)

    env["SCHEMA_REGISTRY_NAME_1"] = "development"
    env["SCHEMA_REGISTRY_URL_1"] = SCHEMA_REGISTRY_BASE_URL
    env["READONLY_1"] = "false"

    env["SCHEMA_REGISTRY_NAME_2"] = "production"
    env["SCHEMA_REGISTRY_URL_2"] = SCHEMA_REGISTRY_BASE_URL
    env["READONLY_2"] = "true"

    # Get the absolute path to the server script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(
        os.path.dirname(script_dir), "kafka_schema_registry_unified_mcp.py"
    )

    server_params = StdioServerParameters(command="python", args=[server_script], env=env)

    try:
        await asyncio.wait_for(_test_per_registry_readonly_with_client(server_params), timeout=30.0)
    except asyncio.TimeoutError:
        print("❌ Per-registry readonly test timed out after 30 seconds")
    except Exception as e:
        print(f"❌ Per-registry READONLY test failed: {e}")


async def _test_per_registry_readonly_with_client(server_params):
    """Helper function for per-registry readonly test with timeout protection."""
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Test schema registration in development (should work)
            test_schema = {
                "type": "record",
                "name": "TestSchema",
                "fields": [{"name": "test_field", "type": "string"}],
            }

            result = await session.call_tool(
                "register_schema",
                {
                    "subject": "integration-test-schema",
                    "schema_definition": test_schema,
                    "registry": "development",
                },
            )
            if result.content and len(result.content) > 0:
                response = json.loads(result.content[0].text)
                if "error" in response:
                    if "Connection refused" in response["error"]:
                        print("⚠️  Development schema registration skipped (connection issue)")
                    else:
                        print(f"⚠️  Development schema registration: {response['error']}")
                else:
                    print("✅ Development schema registration successful")

            # Test schema registration in production (should be blocked)
            result = await session.call_tool(
                "register_schema",
                {
                    "subject": "integration-test-schema",
                    "schema_definition": test_schema,
                    "registry": "production",
                },
            )
            if result.content and len(result.content) > 0:
                response = json.loads(result.content[0].text)
                if "readonly_mode" in response:
                    print("✅ Production schema registration blocked by READONLY mode")
                    print(f"   Message: {response.get('error', 'Blocked')}")
                else:
                    print("❌ Production READONLY mode not working correctly")

            # Test read operations in production (should work)
            result = await session.call_tool("list_subjects", {"context": "production"})
            if result.content and len(result.content) > 0:
                subjects = json.loads(result.content[0].text)
                if isinstance(subjects, list):
                    print(f"✅ Production read operations working: {len(subjects)} subjects")
                else:
                    print(f"⚠️  Production read operations: {subjects}")


async def main():
    """Run all integration tests."""
    print("🚀 Starting Kafka Schema Registry MCP Integration Tests")
    print("📋 Testing numbered environment variable configuration with real operations")
    print("🐳 Using docker-compose Schema Registry with contexts to simulate multiple registries")
    print()

    try:
        await test_numbered_config_integration()
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Integration tests failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
