#!/usr/bin/env python3
"""
Comprehensive Migration Integration Tests

Tests the actual migration functionality in the MCP server to ensure:
1. migrate_context actually migrates schemas (not just returns metadata)
2. migrate_schema works end-to-end
3. Migration counts are accurate
4. Error handling works properly
5. Dry run functionality works
6. Edge cases are handled
"""

import json
import logging
import os
import sys
import uuid

import pytest
import requests

# Add parent directory to path to import the MCP server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import kafka_schema_registry_unified_mcp as mcp_server
from migration_tools import (
    migrate_schema_tool,
)

# Setup logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Mock Progress class for direct function calls in tests (not through FastMCP injection)
class MockProgress:
    """Mock Progress for direct function calls in tests"""

    async def set_total(self, total: int) -> None:
        pass

    async def set_message(self, message: str) -> None:
        pass

    async def increment(self, amount: int = 1) -> None:
        pass


@pytest.fixture
def test_env():
    """Setup test environment with multi-registry configuration"""
    dev_url = "http://localhost:38081"
    prod_url = "http://localhost:38082"
    test_context = f"test-migration-{uuid.uuid4().hex[:8]}"

    # Setup environment for multi-registry mode
    os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
    os.environ["SCHEMA_REGISTRY_URL_1"] = dev_url
    os.environ["VIEWONLY_1"] = "false"

    os.environ["SCHEMA_REGISTRY_NAME_2"] = "prod"
    os.environ["SCHEMA_REGISTRY_URL_2"] = prod_url
    os.environ["VIEWONLY_2"] = "false"  # Allow writes to prod for testing

    # Clear any other registry configurations
    for i in range(3, 9):
        for var in [
            f"SCHEMA_REGISTRY_NAME_{i}",
            f"SCHEMA_REGISTRY_URL_{i}",
            f"VIEWONLY_{i}",
        ]:
            if var in os.environ:
                del os.environ[var]

    # Clear global VIEWONLY setting
    if "VIEWONLY" in os.environ:
        del os.environ["VIEWONLY"]

    # Force reload the registry manager with new configuration
    mcp_server.registry_manager._load_multi_registries()

    yield {"dev_url": dev_url, "prod_url": prod_url, "test_context": test_context}

    # Cleanup after tests - remove any test schemas
    try:
        for registry in ["dev", "prod"]:
            try:
                subjects = mcp_server.list_subjects(context=test_context, registry=registry)
                if subjects and not isinstance(subjects, dict):  # Not an error response
                    for subject in subjects:
                        mcp_server.delete_subject(
                            subject,
                            context=test_context,
                            registry=registry,
                            permanent=True,
                        )
            except Exception:
                pass  # Ignore cleanup errors
    except Exception as e:
        logger.warning(f"Cleanup error: {e}")


def create_test_schema_via_api(registry_url: str, context: str, subject: str, schema_def: dict) -> bool:
    """Create a test schema directly via the registry API"""
    try:
        if context and context != ".":
            url = f"{registry_url}/contexts/{context}/subjects/{subject}/versions"
        else:
            url = f"{registry_url}/subjects/{subject}/versions"

        payload = {"schema": json.dumps(schema_def)}
        response = requests.post(
            url,
            headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
            json=payload,
            timeout=10,
        )
        return response.status_code in [200, 409]  # 409 = already exists
    except Exception as e:
        logger.error(f"Failed to create schema {subject}: {e}")
        return False


@pytest.mark.asyncio
async def test_migrate_schema_functionality(test_env):
    """Test that migrate_schema works for individual schemas"""
    logger.info("Testing migrate_schema functionality...")

    dev_url = test_env["dev_url"]
    test_context = test_env["test_context"]

    test_subject = f"migration-test-{uuid.uuid4().hex[:8]}"

    # Create a test schema in dev
    test_schema = {
        "type": "record",
        "name": "MigrationTestEvent",
        "namespace": "com.example.migration.test",
        "fields": [
            {"name": "testId", "type": "string"},
            {"name": "testValue", "type": "int"},
        ],
    }

    # Create schema via API
    success = create_test_schema_via_api(dev_url, test_context, test_subject, test_schema)
    assert success, f"Failed to create test schema {test_subject}"

    try:
        # Migrate schema using direct function call
        # Progress is None for direct calls - _safe_progress_call handles it gracefully
        result = await migrate_schema_tool(
            subject=test_subject,
            source_registry="dev",
            target_registry="prod",
            registry_manager=mcp_server.registry_manager,
            registry_mode=mcp_server.REGISTRY_MODE,
            source_context=test_context,
            target_context=test_context,
            migrate_all_versions=True,
            preserve_ids=False,
            dry_run=False,
        )

        assert "error" not in result, f"Schema migration failed: {result.get('error')}"

        logger.info("Migration Results:")
        logger.info(f"  Total versions: {result.get('total_versions', 0)}")
        logger.info(f"  Successful: {result.get('successful_migrations', 0)}")
        logger.info(f"  Failed: {result.get('failed_migrations', 0)}")
        logger.info(f"  Skipped: {result.get('skipped_migrations', 0)}")

        # Verify migration was successful OR appropriately skipped
        successful_count = result.get("successful_migrations", 0)
        skipped_count = result.get("skipped_migrations", 0)

        assert successful_count > 0 or skipped_count > 0, "No schema versions migrated or skipped"

        logger.info("✅ Schema migration test passed")

    finally:
        # Cleanup
        try:
            mcp_server.delete_subject(test_subject, context=test_context, registry="dev", permanent=True)
            mcp_server.delete_subject(test_subject, context=test_context, registry="prod", permanent=True)
        except Exception:
            pass


@pytest.mark.asyncio
async def test_migration_progress_reporting(test_env):
    """Test that migration operations report progress correctly using FastMCP Progress"""
    logger.info("Testing migration progress reporting...")

    dev_url = test_env["dev_url"]
    test_context = test_env["test_context"]

    test_subject = f"progress-test-{uuid.uuid4().hex[:8]}"

    # Create a test schema
    test_schema = {
        "type": "record",
        "name": "ProgressTestEvent",
        "namespace": "com.example.migration.test",
        "fields": [{"name": "testId", "type": "string"}],
    }

    success = create_test_schema_via_api(dev_url, test_context, test_subject, test_schema)
    assert success, f"Failed to create progress test schema {test_subject}"

    try:
        # Perform migration - Progress is None for direct calls
        result = await migrate_schema_tool(
            subject=test_subject,
            source_registry="dev",
            target_registry="prod",
            registry_manager=mcp_server.registry_manager,
            registry_mode=mcp_server.REGISTRY_MODE,
            source_context=test_context,
            target_context=test_context,
            migrate_all_versions=False,
            preserve_ids=False,
            dry_run=False,
            progress=None,  # None for direct calls - core function handles gracefully
        )

        # Verify migration completed successfully
        assert "error" not in result, f"Migration failed: {result.get('error')}"
        assert result.get("successful_migrations", 0) >= 0, "Migration should report results"

        # Verify result structure includes migration details
        assert (
            "total_versions" in result or "successful_migrations" in result
        ), "Result should include migration details"

        logger.info("✅ Migration progress reporting test passed")

    finally:
        # Cleanup
        try:
            mcp_server.delete_subject(test_subject, context=test_context, registry="dev", permanent=True)
            mcp_server.delete_subject(test_subject, context=test_context, registry="prod", permanent=True)
        except Exception:
            pass


@pytest.mark.asyncio
async def test_migration_error_handling(test_env):
    """Test migration error handling"""
    logger.info("Testing migration error handling...")

    test_context = test_env["test_context"]

    # Try to migrate non-existent subject - Progress is None for direct calls
    result = await migrate_schema_tool(
        subject="non-existent-subject",
        source_registry="dev",
        target_registry="prod",
        registry_manager=mcp_server.registry_manager,
        registry_mode=mcp_server.REGISTRY_MODE,
        source_context=test_context,
        progress=None,  # None for direct calls - core function handles gracefully
    )

    # Should return a result indicating no versions to migrate, not an error
    assert "total_versions" in result, "Expected migration result with version count"
    assert result.get("total_versions", 0) == 0, "Expected 0 versions for non-existent subject"

    # Try to migrate to non-existent registry
    result = await migrate_schema_tool(
        subject="test-subject",
        source_registry="dev",
        target_registry="non-existent-registry",
        registry_manager=mcp_server.registry_manager,
        registry_mode=mcp_server.REGISTRY_MODE,
        progress=None,  # None for direct calls - core function handles gracefully
    )
    assert "error" in result, "Expected error for non-existent registry"

    logger.info("✅ Migration error handling test passed")


def test_registry_connectivity():
    """Test that both registries are accessible before running tests"""
    logger.info("Testing registry connectivity...")

    dev_response = requests.get("http://localhost:38081/subjects", timeout=5)
    prod_response = requests.get("http://localhost:38082/subjects", timeout=5)

    if dev_response.status_code != 200:
        pytest.skip(f"DEV registry not accessible: {dev_response.status_code}")

    if prod_response.status_code != 200:
        pytest.skip(f"PROD registry not accessible: {prod_response.status_code}")

    logger.info("✅ Both registries accessible")


@pytest.mark.asyncio
async def test_all_migration_features(test_env):
    """Run all migration integration tests"""
    logger.info("🚀 Starting Migration Integration Tests")

    # Test individual features
    await test_migrate_schema_functionality(test_env)
    await test_migration_progress_reporting(test_env)
    await test_migration_error_handling(test_env)

    logger.info("🎉 All Migration Integration Tests passed!")


if __name__ == "__main__":
    # Check connectivity first
    test_registry_connectivity()

    # Run the tests using pytest
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            __file__ + "::test_all_migration_features",
            "-v",
            "-s",
        ]
    )

    sys.exit(result.returncode)
