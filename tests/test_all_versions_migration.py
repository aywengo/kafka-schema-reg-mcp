#!/usr/bin/env python3
"""
All Versions Migration Test

This test validates that the migrate_schema function can preserve
the complete schema evolution history by migrating all versions of schemas,
not just the latest version, when provided with a versions parameter.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import requests

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import kafka_schema_registry_unified_mcp as mcp_server

# Configuration
DEV_REGISTRY_URL = "http://localhost:38081"
PROD_REGISTRY_URL = "http://localhost:38082"


class AllVersionsMigrationTest:
    """Test class for all-versions migration scenarios"""

    def __init__(self):
        # Initialize URLs
        self.dev_url = DEV_REGISTRY_URL
        self.prod_url = PROD_REGISTRY_URL

        # Use default context "." to avoid context prefix issues
        self.source_context = "."
        self.target_context = "."
        self.test_subjects = []

        # Set up environment variables for registry manager
        os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
        os.environ["SCHEMA_REGISTRY_URL_1"] = self.dev_url
        os.environ["SCHEMA_REGISTRY_NAME_2"] = "prod"
        os.environ["SCHEMA_REGISTRY_URL_2"] = self.prod_url
        os.environ["READONLY_2"] = "false"  # Allow writes to prod for testing

        # Reinitialize registry manager with test config
        mcp_server.registry_manager._load_multi_registries()

        # Initialize registry manager
        self.registry_manager = mcp_server.registry_manager

    async def setup_test_contexts(self):
        """No need to create contexts when using default context."""
        print(f"\n=== Using Default Contexts ===")
        print(f"✓ Source context: {self.source_context} (default)")
        print(f"✓ Target context: {self.target_context} (default)")
        return True

    async def create_schema_evolution(self, subject: str, num_versions: int = 3):
        """Create multiple versions of a schema for testing."""
        import copy

        # Create initial schema
        base_schema = {
            "type": "record",
            "name": "TestRecord",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "name", "type": "string"},
            ],
        }

        # Create multiple versions
        for i in range(num_versions):
            schema = copy.deepcopy(base_schema)
            # Add a new field for each version (ensure unique field name, and make it optional for compatibility)
            for j in range(i + 1):
                schema["fields"].append(
                    {"name": f"field_{j}", "type": "string", "default": ""}
                )
            # Register schema using the top-level function
            result = mcp_server.register_schema(
                subject=subject,
                schema_definition=schema,
                schema_type="AVRO",
                context=self.source_context,
                registry="dev",
            )
            if "error" in result:
                raise Exception(
                    f"Failed to register schema version {i+1}: {result['error']}"
                )
            print(f"✓ Registered schema version {i+1}")
        return True

    async def verify_schema_versions(
        self, subject: str, registry: str, context: str, expected_versions: int
    ):
        """Verify that a schema has the expected number of versions."""
        versions = mcp_server.get_schema_versions(
            subject, context=context, registry=registry
        )
        if isinstance(versions, dict) and "error" in versions:
            raise Exception(f"Error getting versions: {versions['error']}")
        if len(versions) != expected_versions:
            raise Exception(
                f"Expected {expected_versions} versions, got {len(versions)}"
            )
        print(f"✓ Verified {len(versions)} versions in {registry} registry")
        return True

    async def test_all_versions_migration(self):
        """Test migration of all versions."""
        print("\n=== Testing All Versions Migration ===")

        # Create test schemas
        subject = f"test-all-versions-{uuid.uuid4().hex[:6]}"
        self.test_subjects.append(subject)

        # Create schema versions in source context
        await self.create_schema_evolution(subject)

        # Verify source has multiple versions
        await self.verify_schema_versions(subject, "dev", self.source_context, 3)

        # migrate_context now generates Docker config, so we use migrate_schema directly
        # First get all versions
        versions = mcp_server.get_schema_versions(
            subject, context=self.source_context, registry="dev"
        )
        if isinstance(versions, dict) and "error" in versions:
            raise Exception(f"Failed to get versions: {versions['error']}")

        print(f"✓ Found {len(versions)} versions to migrate: {versions}")

        # Migrate the schema with all versions
        result = mcp_server.migrate_schema(
            subject=subject,
            source_registry="dev",
            target_registry="prod",
            source_context=self.source_context,
            target_context=self.target_context,
            preserve_ids=True,
            dry_run=False,
            versions=versions,  # Pass all versions to migrate
        )

        if "error" in result:
            raise Exception(f"Migration failed: {result['error']}")

        # Wait for async task to complete
        if "task_id" in result:
            print(f"✓ Migration started with task ID: {result['task_id']}")

            # Poll for task completion
            max_wait = 30  # seconds
            poll_interval = 1  # second
            elapsed = 0

            while elapsed < max_wait:
                task_status = await mcp_server.get_task_progress(result["task_id"])

                if "error" in task_status:
                    raise Exception(
                        f"Failed to get task status: {task_status['error']}"
                    )

                status = task_status.get("status", "")
                progress = task_status.get("progress_percent", 0)

                print(f"  Migration progress: {progress}% - {status}")

                if status in ["completed", "failed", "cancelled"]:
                    if status != "completed":
                        raise Exception(
                            f"Migration task {status}: {task_status.get('error', 'Unknown error')}"
                        )
                    break

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

            if elapsed >= max_wait:
                raise Exception("Migration task timed out")

            print("✓ Migration task completed")

        # Verify target has all versions
        await self.verify_schema_versions(subject, "prod", self.target_context, 3)

        print("✓ All versions migration successful")
        return True

    async def cleanup_test_contexts(self):
        """Clean up test subjects from both registries."""
        print("\n=== Cleaning Up Test Subjects ===")

        # Clean up subjects from both registries
        for registry in ["dev", "prod"]:
            for subject in self.test_subjects:
                try:
                    result = await mcp_server.delete_subject(
                        subject, context=self.source_context, registry=registry
                    )
                    if isinstance(result, dict) and "error" in result:
                        # It's ok if subject doesn't exist in target
                        if "not found" not in str(result["error"]).lower():
                            print(
                                f"Warning: Failed to delete {subject} from {registry}: {result['error']}"
                            )
                    else:
                        print(f"✓ Deleted {subject} from {registry}")
                except Exception as e:
                    # It's ok if subject doesn't exist
                    if "not found" not in str(e).lower():
                        print(
                            f"Warning: Failed to delete {subject} from {registry}: {str(e)}"
                        )

        return True

    async def run_all_tests(self):
        """Run all tests."""
        try:
            # Set up test contexts
            await self.setup_test_contexts()

            # Run tests
            await self.test_all_versions_migration()

            print("\n=== All Tests Completed Successfully ===")
            return True

        except Exception as e:
            print(f"\n❌ Test Failed: {str(e)}")
            return False

        finally:
            # Clean up
            await self.cleanup_test_contexts()


async def main():
    test = AllVersionsMigrationTest()
    success = await test.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
