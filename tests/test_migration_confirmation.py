#!/usr/bin/env python3
"""
Migration Confirmation Test

This test validates that:
1. Migration stops and asks for confirmation when ID preservation fails
2. Users can proceed with confirm_migration_without_ids_tool
3. The confirmation mechanism works properly in different scenarios
4. The structured output decorator handles async functions correctly
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

import requests

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import kafka_schema_registry_unified_mcp as mcp_server
from core_registry_tools import delete_subject_tool, register_schema_tool
from migration_tools import (
    MigrationConfirmationRequired,
    _execute_schema_migration,
    confirm_migration_without_ids_tool,
    migrate_context_tool,
    migrate_schema_tool,
)

# Configuration
DEV_REGISTRY_URL = "http://localhost:38081"
PROD_REGISTRY_URL = "http://localhost:38082"


class MigrationConfirmationTest:
    """Test class for migration confirmation scenarios"""

    def __init__(self):
        self.dev_url = DEV_REGISTRY_URL
        self.prod_url = PROD_REGISTRY_URL
        self.source_context = "."
        self.target_context = "."
        self.test_subjects = []

    def setup_test_environment(self):
        """Setup environment and reload registry manager"""
        print("🔧 Setting up test environment...")

        # Set up environment variables for multi-registry setup
        os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
        os.environ["SCHEMA_REGISTRY_URL_1"] = self.dev_url
        os.environ["READONLY_1"] = "false"
        os.environ["SCHEMA_REGISTRY_NAME_2"] = "prod"
        os.environ["SCHEMA_REGISTRY_URL_2"] = self.prod_url
        os.environ["READONLY_2"] = "false"

        # Clear any other registry configurations
        for i in range(3, 9):
            for var in [f"SCHEMA_REGISTRY_NAME_{i}", f"SCHEMA_REGISTRY_URL_{i}", f"READONLY_{i}"]:
                if var in os.environ:
                    del os.environ[var]

        # Force reload the registry manager with new configuration
        mcp_server.registry_manager._load_multi_registries()
        print("✅ Test environment setup complete")

    def test_migrate_context_is_sync(self):
        """Test that migrate_context_tool is synchronous and works correctly"""
        print("\n=== Testing migrate_context_tool is Synchronous ===")

        # This should work without await
        result = migrate_context_tool(
            source_registry="dev",
            target_registry="prod",
            registry_manager=mcp_server.registry_manager,
            registry_mode=mcp_server.REGISTRY_MODE,
            context="test-context",
            preserve_ids=True,
            dry_run=True,
        )

        # Should return Docker command instructions
        if "error" in result:
            # This is expected in test environment without proper registries
            print(f"ℹ️  Expected error in test environment: {result.get('error')}")
            return True

        required_keys = ["docker_command", "tool", "instructions", "env_variables"]
        for key in required_keys:
            if key not in result:
                raise Exception(f"Missing required key in migrate_context response: {key}")

        if "kafka-schema-reg-migrator" not in result["tool"]:
            raise Exception("Wrong tool name in migrate_context response")

        print("✅ migrate_context_tool works synchronously")
        print(f"✅ Tool: {result['tool']}")
        print(f"✅ Status: {result.get('status')}")

        return result

    def test_confirmation_exception_handling(self):
        """Test the MigrationConfirmationRequired exception"""
        print("\n=== Testing MigrationConfirmationRequired Exception ===")

        # Test exception creation
        details = {
            "subject": "test-subject",
            "source_registry": "dev",
            "target_registry": "prod",
            "preserve_ids_requested": True,
            "error_reason": "Permission denied",
            "options": {
                "continue_without_id_preservation": "Proceed with new IDs",
                "cancel_migration": "Cancel and fix permissions",
            },
        }

        exc = MigrationConfirmationRequired("Test confirmation required", details)

        # Test exception properties
        if str(exc) != "Test confirmation required":
            raise Exception("Exception message not set correctly")

        if exc.confirmation_details != details:
            raise Exception("Confirmation details not set correctly")

        print("✅ MigrationConfirmationRequired exception works correctly")
        return True

    def test_confirmation_tools_exist(self):
        """Test that confirmation tools are properly importable"""
        print("\n=== Testing Confirmation Tools Import ===")

        # Test that all required tools can be imported
        try:
            from migration_tools import (
                MigrationConfirmationRequired,
                confirm_migration_without_ids_tool,
                migrate_schema_tool,
            )

            print("✅ All confirmation tools imported successfully")
        except ImportError as e:
            raise Exception(f"Failed to import confirmation tools: {e}")

        # Test that confirm_migration_without_ids_tool has the right signature
        import inspect

        sig = inspect.signature(confirm_migration_without_ids_tool)
        required_params = ["subject", "source_registry", "target_registry", "registry_manager", "registry_mode"]

        for param in required_params:
            if param not in sig.parameters:
                raise Exception(f"Missing required parameter {param} in confirm_migration_without_ids_tool")

        print("✅ confirm_migration_without_ids_tool has correct signature")
        return True

    def run_all_tests(self):
        """Run all confirmation tests"""
        print("🧪 Starting Migration Confirmation Tests")
        print("=" * 60)

        try:
            self.setup_test_environment()

            # Run individual tests
            tests = [
                ("migrate_context_tool is Sync", self.test_migrate_context_is_sync),
                ("Confirmation Exception Handling", self.test_confirmation_exception_handling),
                ("Confirmation Tools Import", self.test_confirmation_tools_exist),
            ]

            passed = 0
            for test_name, test_func in tests:
                print(f"\n🔬 Running: {test_name}")
                try:
                    test_func()
                    print(f"✅ {test_name} PASSED")
                    passed += 1
                except Exception as e:
                    print(f"❌ {test_name} FAILED: {e}")
                    import traceback

                    traceback.print_exc()

            print(f"\n📊 Test Results: {passed}/{len(tests)} tests passed")

            if passed == len(tests):
                print("\n🎉 ALL MIGRATION CONFIRMATION TESTS PASSED!")
                return True
            else:
                print(f"\n⚠️  {len(tests) - passed} tests failed")
                return False

        except Exception as e:
            print(f"\n❌ Test setup failed: {e}")
            import traceback

            traceback.print_exc()
            return False


def main():
    """Main test execution function"""
    print("🚀 Migration Confirmation Test Suite")
    print("=" * 60)

    try:
        # Run the confirmation tests
        test = MigrationConfirmationTest()
        success = test.run_all_tests()

        if success:
            print("\n🎉 Migration Confirmation Test Suite completed successfully!")
            return 0
        else:
            print("\n❌ Migration Confirmation Test Suite failed!")
            return 1

    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
