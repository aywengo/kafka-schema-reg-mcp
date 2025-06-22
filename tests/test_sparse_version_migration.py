#!/usr/bin/env python3
"""
Sparse Version Migration Test

This test reproduces the issue where schemas with sparse version numbers
(e.g., versions [3, 4, 5] when versions 1 and 2 were deleted) get shifted
to sequential versions starting from 1 in the target registry.

Issue: If source has versions [3, 4, 5], they should remain [3, 4, 5] in target,
not be shifted to [1, 2, 3].
"""

import asyncio
import copy
import os
import sys
import uuid
from pathlib import Path

import requests

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import kafka_schema_registry_unified_mcp as mcp_server
from core_registry_tools import (
    delete_subject_tool,
    get_schema_versions_tool,
    register_schema_tool,
)
from migration_tools import get_migration_status_tool, migrate_schema_tool

# Configuration
DEV_REGISTRY_URL = "http://localhost:38081"
PROD_REGISTRY_URL = "http://localhost:38082"


class SparseVersionMigrationTest:
    """Test class for sparse version migration scenarios"""

    def __init__(self):
        # Initialize URLs
        self.dev_url = DEV_REGISTRY_URL
        self.prod_url = PROD_REGISTRY_URL

        # Use default context "." to avoid context prefix issues
        self.source_context = "."
        self.target_context = "."
        self.test_subjects = []

    def setup_test_environment(self):
        """Setup environment and reload registry manager"""
        # Set up environment variables for multi-registry setup
        os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
        os.environ["SCHEMA_REGISTRY_URL_1"] = self.dev_url
        os.environ["READONLY_1"] = "false"
        os.environ["SCHEMA_REGISTRY_NAME_2"] = "prod"
        os.environ["SCHEMA_REGISTRY_URL_2"] = self.prod_url
        os.environ["READONLY_2"] = "false"

        # Clear any other registry configurations
        for i in range(3, 9):
            for var in [
                f"SCHEMA_REGISTRY_NAME_{i}",
                f"SCHEMA_REGISTRY_URL_{i}",
                f"READONLY_{i}",
            ]:
                if var in os.environ:
                    del os.environ[var]

        # Clear any global READONLY setting
        os.environ.pop("READONLY", None)

        # Force reload the registry manager with new configuration
        mcp_server.registry_manager._load_multi_registries()

    def setup_test_contexts(self):
        """No need to create contexts when using default context."""
        print("\n=== Using Default Contexts ===")
        print(f"✓ Source context: {self.source_context} (default)")
        print(f"✓ Target context: {self.target_context} (default)")
        return True

    def create_sparse_version_schema(self, subject: str):
        """Create a schema with sparse versions (3, 4, 5) by creating 5 versions then deleting 1 and 2."""
        print(f"\n--- Creating sparse version schema for {subject} ---")

        # Create initial schema
        base_schema = {
            "type": "record",
            "name": "SparseTestRecord",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "name", "type": "string"},
            ],
        }

        # Create 5 versions first
        for i in range(5):
            schema = copy.deepcopy(base_schema)
            # Add a unique field for each version
            schema["fields"].append(
                {"name": f"version_{i+1}_field", "type": "string", "default": f"v{i+1}"}
            )

            # Register schema using direct tool function call
            result = register_schema_tool(
                subject=subject,
                schema_definition=schema,
                schema_type="AVRO",
                context=self.source_context,
                registry="dev",
                registry_manager=mcp_server.registry_manager,
                registry_mode=mcp_server.REGISTRY_MODE,
            )

            if "error" in result:
                raise Exception(
                    f"Failed to register schema version {i+1}: {result['error']}"
                )
            print(f"✓ Registered schema version {i+1}")

        # Verify we have 5 versions
        versions = get_schema_versions_tool(
            subject=subject,
            context=self.source_context,
            registry="dev",
            registry_manager=mcp_server.registry_manager,
            registry_mode=mcp_server.REGISTRY_MODE,
        )

        if isinstance(versions, dict) and "error" in versions:
            raise Exception(f"Error getting versions: {versions['error']}")
        if len(versions) != 5:
            raise Exception(f"Expected 5 versions, got {len(versions)}")
        print(f"✓ Confirmed 5 versions exist: {versions}")

        # Now delete versions 1 and 2 to create sparse version set [3, 4, 5]
        print("\n--- Deleting versions 1 and 2 to create sparse set ---")

        # Get registry client info for direct deletion
        try:
            # Delete version 1
            delete_url1 = f"{self.dev_url}/subjects/{subject}/versions/1"
            response1 = requests.delete(delete_url1)
            if response1.status_code == 200:
                print("✓ Deleted version 1")
            else:
                print(
                    f"Warning: Could not delete version 1: {response1.status_code} - {response1.text}"
                )
        except Exception as e:
            print(f"Warning: Error deleting version 1: {e}")

        try:
            # Delete version 2
            delete_url2 = f"{self.dev_url}/subjects/{subject}/versions/2"
            response2 = requests.delete(delete_url2)
            if response2.status_code == 200:
                print("✓ Deleted version 2")
            else:
                print(
                    f"Warning: Could not delete version 2: {response2.status_code} - {response2.text}"
                )
        except Exception as e:
            print(f"Warning: Error deleting version 2: {e}")

        # Verify we now have sparse versions [3, 4, 5]
        final_versions = get_schema_versions_tool(
            subject=subject,
            context=self.source_context,
            registry="dev",
            registry_manager=mcp_server.registry_manager,
            registry_mode=mcp_server.REGISTRY_MODE,
        )

        if isinstance(final_versions, dict) and "error" in final_versions:
            raise Exception(f"Error getting final versions: {final_versions['error']}")

        print(f"✓ Final source versions after deletion: {sorted(final_versions)}")

        # Ensure we have exactly versions [3, 4, 5]
        expected_versions = [3, 4, 5]
        if sorted(final_versions) != expected_versions:
            raise Exception(
                f"Expected sparse versions {expected_versions}, got {sorted(final_versions)}"
            )

        print(f"✓ Successfully created sparse version set: {sorted(final_versions)}")
        return final_versions

    def verify_sparse_versions_preserved(self, subject: str, expected_versions: list):
        """Verify that the target registry has the exact same version numbers as source."""
        target_versions = get_schema_versions_tool(
            subject=subject,
            context=self.target_context,
            registry="prod",
            registry_manager=mcp_server.registry_manager,
            registry_mode=mcp_server.REGISTRY_MODE,
        )

        if isinstance(target_versions, dict) and "error" in target_versions:
            raise Exception(
                f"Error getting target versions: {target_versions['error']}"
            )

        sorted_target = sorted(target_versions)
        sorted_expected = sorted(expected_versions)

        print(f"  Source versions: {sorted_expected}")
        print(f"  Target versions: {sorted_target}")

        if sorted_target != sorted_expected:
            raise Exception(
                f"VERSION MISMATCH: Expected {sorted_expected}, got {sorted_target}. "
                f"This indicates that sparse versions were not preserved during migration!"
            )

        print("✓ Sparse versions correctly preserved in target")
        return True

    def test_sparse_version_migration(self):
        """Test that sparse version numbers are preserved during migration."""
        print("\n=== Testing Sparse Version Migration ===")

        # Create test subject
        subject = f"sparse-test-{uuid.uuid4().hex[:8]}"
        self.test_subjects.append(subject)

        # Create sparse version schema in source
        sparse_versions = self.create_sparse_version_schema(subject)
        print(
            f"✓ Created sparse version schema with versions: {sorted(sparse_versions)}"
        )

        # Migrate the schema with sparse versions using direct function call
        print(f"\n--- Migrating sparse schema {subject} ---")
        migration_result = migrate_schema_tool(
            subject=subject,
            source_registry="dev",
            target_registry="prod",
            registry_manager=mcp_server.registry_manager,
            registry_mode=mcp_server.REGISTRY_MODE,
            source_context=self.source_context,
            target_context=self.target_context,
            preserve_ids=True,  # This should preserve version numbers
            dry_run=False,
            versions=sparse_versions,  # Pass specific versions to migrate
        )

        if "error" in migration_result:
            raise Exception(f"Migration failed: {migration_result['error']}")

        # Check for task tracking
        if "migration_id" in migration_result:
            print(
                f"✓ Migration started with task ID: {migration_result['migration_id']}"
            )

            # Check task status
            status = get_migration_status_tool(
                migration_result["migration_id"], mcp_server.REGISTRY_MODE
            )
            if status and "error" not in status:
                print(f"✓ Migration task status: {status.get('status', 'unknown')}")

        print("✓ Migration completed")

        # Verify that sparse versions are preserved (crucial test)
        print("\n--- Verifying sparse versions preserved ---")
        self.verify_sparse_versions_preserved(subject, sparse_versions)

        print("✅ Sparse version migration test passed!")
        return True

    def cleanup_test_subjects(self):
        """Clean up test subjects from both registries."""
        print("\n=== Cleaning Up Test Subjects ===")

        for subject in self.test_subjects:
            # Clean up from dev registry
            try:
                result = asyncio.run(
                    delete_subject_tool(
                        subject=subject,
                        registry="dev",
                        permanent=True,
                        registry_manager=mcp_server.registry_manager,
                        registry_mode=mcp_server.REGISTRY_MODE,
                    )
                )
                print(f"✓ Cleaned up {subject} from dev")
            except Exception as e:
                print(f"Warning: Failed to delete {subject} from dev: {e}")

            # Clean up from prod registry
            try:
                result = asyncio.run(
                    delete_subject_tool(
                        subject=subject,
                        registry="prod",
                        permanent=True,
                        registry_manager=mcp_server.registry_manager,
                        registry_mode=mcp_server.REGISTRY_MODE,
                    )
                )
                print(f"✓ Cleaned up {subject} from prod")
            except Exception as e:
                print(f"Warning: Failed to delete {subject} from prod: {e}")

    def run_all_tests(self):
        """Run all sparse version migration tests."""
        print("🧪 Starting Sparse Version Migration Tests")
        print("=" * 50)

        try:
            self.setup_test_environment()
            self.setup_test_contexts()
            self.test_sparse_version_migration()
            print("\n✅ All tests passed!")
            return True
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            self.cleanup_test_subjects()


def test_registry_connectivity():
    """Test that both registries are accessible before running tests"""
    print("🔍 Testing registry connectivity...")

    dev_response = requests.get("http://localhost:38081/subjects", timeout=5)
    prod_response = requests.get("http://localhost:38082/subjects", timeout=5)

    if dev_response.status_code != 200:
        raise Exception(f"DEV registry not accessible: {dev_response.status_code}")

    if prod_response.status_code != 200:
        raise Exception(f"PROD registry not accessible: {prod_response.status_code}")

    print("✅ Both registries accessible")


def main():
    """Main test execution function."""
    print("🔄 Sparse Version Migration Test")
    print("=" * 50)

    try:
        # Check connectivity first
        test_registry_connectivity()

        # Run the test
        test = SparseVersionMigrationTest()
        success = test.run_all_tests()

        if success:
            print("\n🎉 Sparse Version Migration Test completed successfully!")
            return 0
        else:
            print("\n❌ Sparse Version Migration Test failed!")
            return 1

    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
