#!/usr/bin/env python3
"""
All Versions Migration Test

This test validates that the migrate_schema function can preserve
the complete schema evolution history by migrating all versions of schemas,
not just the latest version, when provided with a versions parameter.
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

    def setup_test_environment(self):
        """Setup environment and reload registry manager"""
        # Set up environment variables for multi-registry setup
        os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
        os.environ["SCHEMA_REGISTRY_URL_1"] = self.dev_url
        os.environ["VIEWONLY_1"] = "false"
        os.environ["SCHEMA_REGISTRY_NAME_2"] = "prod"
        os.environ["SCHEMA_REGISTRY_URL_2"] = self.prod_url
        os.environ["VIEWONLY_2"] = "false"

        # Clear any other registry configurations
        for i in range(3, 9):
            for var in [
                f"SCHEMA_REGISTRY_NAME_{i}",
                f"SCHEMA_REGISTRY_URL_{i}",
                f"VIEWONLY_{i}",
            ]:
                if var in os.environ:
                    del os.environ[var]

        # Clear any global VIEWONLY setting
        os.environ.pop("VIEWONLY", None)

        # Force reload the registry manager with new configuration
        mcp_server.registry_manager._load_multi_registries()

    def setup_test_contexts(self):
        """No need to create contexts when using default context."""
        print("\n=== Using Default Contexts ===")
        print(f"✓ Source context: {self.source_context} (default)")
        print(f"✓ Target context: {self.target_context} (default)")
        return True

    def create_schema_evolution(self, subject: str, num_versions: int = 3):
        """Create multiple versions of a schema for testing using direct function calls."""
        print(f"--- Creating schema evolution for {subject} ---")

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
                schema["fields"].append({"name": f"field_{j}", "type": "string", "default": ""})

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
                raise Exception(f"Failed to register schema version {i+1}: {result['error']}")
            print(f"✓ Registered schema version {i+1}")
        return True

    def verify_schema_versions(self, subject: str, registry: str, context: str, expected_versions: int):
        """Verify that a schema has the expected number of versions."""
        versions_result = get_schema_versions_tool(
            subject=subject,
            context=context,
            registry=registry,
            registry_manager=mcp_server.registry_manager,
            registry_mode=mcp_server.REGISTRY_MODE,
        )

        if isinstance(versions_result, dict):
            if "error" in versions_result:
                raise Exception(f"Error getting versions: {versions_result['error']}")
            elif "versions" in versions_result:
                versions = versions_result["versions"]
            else:
                versions = versions_result
        else:
            versions = versions_result

        if len(versions) != expected_versions:
            raise Exception(f"Expected {expected_versions} versions, got {len(versions)}")
        print(f"✓ Verified {len(versions)} versions in {registry} registry")
        return True

    def test_all_versions_migration(self):
        """Test migration of all versions."""
        print("\n=== Testing All Versions Migration ===")

        # Create test schemas
        subject = f"test-all-versions-{uuid.uuid4().hex[:6]}"
        self.test_subjects.append(subject)

        # Create schema versions in source context
        self.create_schema_evolution(subject)

        # Verify source has multiple versions
        self.verify_schema_versions(subject, "dev", self.source_context, 3)

        # Get all versions
        versions_result = get_schema_versions_tool(
            subject=subject,
            context=self.source_context,
            registry="dev",
            registry_manager=mcp_server.registry_manager,
            registry_mode=mcp_server.REGISTRY_MODE,
        )

        if isinstance(versions_result, dict):
            if "error" in versions_result:
                raise Exception(f"Failed to get versions: {versions_result['error']}")
            elif "versions" in versions_result:
                versions = versions_result["versions"]
            else:
                versions = versions_result
        else:
            versions = versions_result

        print(f"✓ Found {len(versions)} versions to migrate: {versions}")

        # Migrate the schema with all versions using direct function call
        migration_result = migrate_schema_tool(
            subject=subject,
            source_registry="dev",
            target_registry="prod",
            registry_manager=mcp_server.registry_manager,
            registry_mode=mcp_server.REGISTRY_MODE,
            source_context=self.source_context,
            target_context=self.target_context,
            preserve_ids=True,
            dry_run=False,
            versions=versions,  # Pass all versions to migrate
        )

        # Handle confirmation required for ID preservation
        if "error" in migration_result:
            if migration_result.get("error_type") == "confirmation_required":
                print("⚠️  ID preservation failed, proceeding without ID preservation")
                # Import the confirmation tool
                from migration_tools import confirm_migration_without_ids_tool

                # Retry migration without ID preservation
                migration_result = confirm_migration_without_ids_tool(
                    subject=subject,
                    source_registry="dev",
                    target_registry="prod",
                    registry_manager=mcp_server.registry_manager,
                    registry_mode=mcp_server.REGISTRY_MODE,
                    source_context=self.source_context,
                    target_context=self.target_context,
                    dry_run=False,
                    versions=versions,
                )

                if "error" in migration_result:
                    raise Exception(f"Migration failed even without ID preservation: {migration_result['error']}")
                else:
                    print("✓ Migration completed without ID preservation")
            else:
                raise Exception(f"Migration failed: {migration_result['error']}")

        # Check for task tracking
        if "migration_id" in migration_result:
            print(f"✓ Migration started with task ID: {migration_result['migration_id']}")

            # Check task status
            status = get_migration_status_tool(migration_result["migration_id"], mcp_server.REGISTRY_MODE)
            if status and "error" not in status:
                print(f"✓ Migration task status: {status.get('status', 'unknown')}")

        print("✓ Migration completed")

        # Verify target has all versions
        self.verify_schema_versions(subject, "prod", self.target_context, 3)

        print("✓ All versions migration successful")
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
        """Run all migration tests."""
        print("🧪 Starting All Versions Migration Tests")
        print("=" * 50)

        try:
            self.setup_test_environment()
            self.setup_test_contexts()
            self.test_all_versions_migration()
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
    print("🔄 All Versions Migration Test")
    print("=" * 50)

    try:
        # Check connectivity first
        test_registry_connectivity()

        # Run the test
        test = AllVersionsMigrationTest()
        success = test.run_all_tests()

        if success:
            print("\n🎉 All Versions Migration Test completed successfully!")
            return 0
        else:
            print("\n❌ All Versions Migration Test failed!")
            return 1

    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
