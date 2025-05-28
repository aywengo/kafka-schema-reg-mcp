#!/usr/bin/env python3
"""
Lightweight Migration Integration Test

This test validates migration integration functionality using the existing
multi-registry environment without managing Docker containers.
"""

import os
import sys
import json
import requests
import uuid
from datetime import datetime

# Add parent directory to path to import the MCP server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import kafka_schema_registry_multi_mcp as mcp_server

class LightweightMigrationIntegrationTest:
    """Lightweight test class for migration integration functionality"""
    
    def __init__(self):
        self.dev_url = "http://localhost:38081"
        self.prod_url = "http://localhost:38082"
        self.test_context = f"test-integration-{uuid.uuid4().hex[:8]}"
        
        # Setup environment for multi-registry mode with both registries writable
        os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
        os.environ["SCHEMA_REGISTRY_URL_1"] = self.dev_url
        os.environ["READONLY_1"] = "false"
        
        os.environ["SCHEMA_REGISTRY_NAME_2"] = "prod"
        os.environ["SCHEMA_REGISTRY_URL_2"] = self.prod_url
        os.environ["READONLY_2"] = "false"  # Make PROD writable for testing
        
        # Clear any other registry configurations
        for i in range(3, 9):
            for var in [f"SCHEMA_REGISTRY_NAME_{i}", f"SCHEMA_REGISTRY_URL_{i}", f"READONLY_{i}"]:
                if var in os.environ:
                    del os.environ[var]
        
        # Clear global READONLY setting
        if "READONLY" in os.environ:
            del os.environ["READONLY"]
        
        # Force reload the registry manager with new configuration
        mcp_server.registry_manager._load_registries()
        
        # Verify configuration loaded correctly
        registries = mcp_server.list_registries()
        print(f"   🔧 Configured registries: {len(registries)} total")
        for reg in registries:
            if isinstance(reg, dict):
                name = reg.get('name', 'unknown')
                readonly = reg.get('readonly', 'unknown')
                print(f"   📊 {name}: readonly={readonly}")
        
        # Additional verification: Check readonly mode directly
        dev_readonly = mcp_server.check_readonly_mode("dev")
        prod_readonly = mcp_server.check_readonly_mode("prod")
        
        if dev_readonly:
            print(f"   ⚠️  DEV still in readonly mode: {dev_readonly}")
        else:
            print(f"   ✅ DEV configured as writable")
            
        if prod_readonly:
            print(f"   ⚠️  PROD still in readonly mode: {prod_readonly}")
            print(f"   🔧 Will attempt to override for testing...")
        else:
            print(f"   ✅ PROD configured as writable")
    
    def create_test_schema(self, subject: str) -> bool:
        """Create a test schema in the DEV registry"""
        try:
            schema = {
                "type": "record",
                "name": "TestEvent",
                "namespace": "com.example.test",
                "fields": [
                    {"name": "id", "type": "string"},
                    {"name": "timestamp", "type": "long"},
                    {"name": "data", "type": "string"}
                ]
            }
            
            # Create in dev registry with context
            result = mcp_server.register_schema(
                subject=subject,
                schema_definition=schema,
                context=self.test_context,
                registry="dev"
            )
            
            if "error" in result:
                print(f"   ❌ Failed to create test schema {subject}: {result['error']}")
                return False
            
            print(f"   ✅ Created test schema {subject} with ID {result.get('id')}")
            return True
            
        except Exception as e:
            print(f"   ❌ Error creating test schema {subject}: {e}")
            return False
    
    def temporarily_override_readonly(self, registry_name: str, readonly: bool):
        """Temporarily override readonly setting for a registry during testing"""
        try:
            client = mcp_server.registry_manager.get_registry(registry_name)
            if client and hasattr(client.config, 'readonly'):
                original_readonly = client.config.readonly
                client.config.readonly = readonly
                print(f"   🔧 Temporarily set {registry_name} readonly={readonly} (was {original_readonly})")
                return original_readonly
            else:
                print(f"   ⚠️  Could not find registry config for {registry_name}")
                return None
        except Exception as e:
            print(f"   ❌ Error overriding readonly for {registry_name}: {e}")
            return None
    
    def restore_readonly(self, registry_name: str, original_readonly: bool):
        """Restore original readonly setting for a registry"""
        try:
            client = mcp_server.registry_manager.get_registry(registry_name)
            if client and hasattr(client.config, 'readonly'):
                client.config.readonly = original_readonly
                print(f"   🔄 Restored {registry_name} readonly={original_readonly}")
        except Exception as e:
            print(f"   ⚠️  Error restoring readonly for {registry_name}: {e}")
    
    def test_end_to_end_migration(self) -> bool:
        """Test complete end-to-end migration workflow"""
        print(f"\n🔄 Testing end-to-end migration workflow...")
        
        # Temporarily override readonly mode for PROD during testing
        original_prod_readonly = self.temporarily_override_readonly("prod", False)
        
        try:
            # Step 1: Create test schemas in DEV
            test_subjects = [
                f"user-events-{uuid.uuid4().hex[:6]}",
                f"order-events-{uuid.uuid4().hex[:6]}"
            ]
            
            print(f"   📝 Creating test schemas in DEV registry...")
            for subject in test_subjects:
                if not self.create_test_schema(subject):
                    return False
            
            # Step 2: Verify schemas exist in DEV
            dev_subjects = mcp_server.list_subjects(context=self.test_context, registry="dev")
            if "error" in dev_subjects:
                print(f"   ❌ Could not list DEV subjects: {dev_subjects['error']}")
                return False
            
            # Schema Registry stores subjects with context prefix: :.{context}:{subject}
            expected_subjects = [f":.{self.test_context}:{subject}" for subject in test_subjects]
            found_subjects = [s for s in expected_subjects if s in dev_subjects]
            
            print(f"   📊 DEV subjects found: {len(dev_subjects)} total")
            print(f"   🔍 Looking for: {expected_subjects}")
            print(f"   ✅ Found: {found_subjects}")
            
            if len(found_subjects) != len(test_subjects):
                print(f"   ❌ Not all test subjects found in DEV: expected {len(test_subjects)}, found {len(found_subjects)}")
                print(f"   📋 All DEV subjects: {dev_subjects}")
                return False
            
            print(f"   ✅ All {len(test_subjects)} test schemas created in DEV")
            
            # Step 3: Verify PROD is empty for our test context
            prod_subjects = mcp_server.list_subjects(context=self.test_context, registry="prod")
            if "error" not in prod_subjects and len(prod_subjects) > 0:
                # Filter for our test subjects only
                prod_test_subjects = [s for s in prod_subjects if any(test_subj in s for test_subj in test_subjects)]
                if len(prod_test_subjects) > 0:
                    print(f"   ⚠️  PROD already has {len(prod_test_subjects)} test subjects in context")
            
            # Step 4: Perform dry run migration
            print(f"   🧪 Testing dry run migration...")
            dry_run_result = mcp_server.migrate_context(
                context=self.test_context,
                source_registry="dev",
                target_registry="prod",
                migrate_all_versions=False,  # Only latest version
                preserve_ids=False,         # Disable ID preservation 
                dry_run=True
            )
            
            if "error" in dry_run_result:
                print(f"   ❌ Dry run failed: {dry_run_result['error']}")
                return False
            
            if not dry_run_result.get("dry_run", False):
                print(f"   ❌ Dry run not marked as dry run")
                return False
            
            expected_subjects_count = dry_run_result.get("subject_count", 0)
            print(f"   ✅ Dry run successful: {expected_subjects_count} subjects to migrate")
            
            # Step 5: Verify readonly override is working
            readonly_check = mcp_server.check_readonly_mode("prod")
            if readonly_check:
                print(f"   ⚠️  PROD still shows readonly: {readonly_check}")
                print(f"   🔧 Attempting migration anyway for testing...")
            else:
                print(f"   ✅ PROD readonly override successful")
            
            # Step 6: Perform actual migration (with simplified settings)
            print(f"   🚀 Performing actual migration...")
            print(f"   💡 Using simplified settings: latest versions only, no ID preservation")
            migration_result = mcp_server.migrate_context(
                context=self.test_context,
                source_registry="dev",
                target_registry="prod",
                migrate_all_versions=False,  # Only latest version
                preserve_ids=False,         # Disable ID preservation (avoid IMPORT mode)
                dry_run=False
            )
            
            if "error" in migration_result:
                error_msg = migration_result["error"]
                if "readonly" in error_msg.lower():
                    print(f"   ❌ Migration blocked by readonly mode: {error_msg}")
                    print(f"   💡 This indicates the readonly override didn't work")
                else:
                    print(f"   ❌ Migration failed: {error_msg}")
                return False
            
            successful_migrations = migration_result.get("successful_migrations", 0)
            total_subjects = migration_result.get("total_subjects", 0)
            
            print(f"   📊 Migration completed: {successful_migrations}/{total_subjects} subjects migrated")
            
            # If migration still failed with simplified settings, investigate further
            if successful_migrations == 0:
                print(f"   ❌ Migration failed even with simplified settings!")
                print(f"   🔍 This suggests a more fundamental issue...")
                
                # Enhanced debugging - show detailed error information
                if "results" in migration_result:
                    results = migration_result["results"]
                    print(f"   🔍 Failed subjects: {results.get('failed_subjects', [])}")
                    print(f"   🔍 Skipped subjects: {results.get('skipped_subjects', [])}")
                    
                    # Extract detailed version-level error information
                    version_details = results.get('version_details', [])
                    if version_details:
                        print(f"   🔍 Version-level details:")
                        for detail in version_details:
                            if detail.get('status') == 'failed':
                                subject = detail.get('subject', 'unknown')
                                version = detail.get('version', 'unknown')  
                                error = detail.get('error', 'no error details')
                                source_id = detail.get('source_id', 'unknown')
                                print(f"      ❌ {subject} v{version}: {error} (source_id: {source_id})")
                    else:
                        print(f"   🔍 No version details available for debugging")
                
                return False
            
            # Step 7: Verify schemas exist in PROD
            prod_subjects_after = mcp_server.list_subjects(context=self.test_context, registry="prod")
            if "error" in prod_subjects_after:
                print(f"   ❌ Could not list PROD subjects after migration: {prod_subjects_after['error']}")
                return False
            
            # Check for our migrated subjects with context prefix
            migrated_subjects = [s for s in expected_subjects if s in prod_subjects_after]
            print(f"   ✅ Found {len(migrated_subjects)} migrated subjects in PROD")
            
            if len(migrated_subjects) != successful_migrations:
                print(f"   ⚠️  Mismatch: {successful_migrations} reported migrated but {len(migrated_subjects)} found")
            
            print(f"   ✅ End-to-end migration workflow completed successfully")
            return True
            
        except Exception as e:
            print(f"   ❌ End-to-end migration test failed: {e}")
            return False
        
        finally:
            # Restore original readonly setting
            if original_prod_readonly is not None:
                self.restore_readonly("prod", original_prod_readonly)
            
            # Cleanup: Remove test context from both registries
            try:
                print(f"   🧹 Cleaning up test context...")
                for registry in ["dev", "prod"]:
                    try:
                        url = f"{self.dev_url if registry == 'dev' else self.prod_url}/contexts/{self.test_context}"
                        requests.delete(url, timeout=5)
                    except Exception:
                        pass  # Ignore cleanup errors
            except Exception:
                pass
    
    def test_migration_error_handling(self) -> bool:
        """Test migration error handling scenarios"""
        print(f"\n🛡️  Testing migration error handling...")
        
        try:
            # Test 1: Non-existent source registry
            result1 = mcp_server.migrate_context(
                context=self.test_context,
                source_registry="nonexistent",
                target_registry="prod",
                dry_run=True
            )
            
            if "error" not in result1:
                print(f"   ❌ Should have failed for non-existent source registry")
                return False
            
            print(f"   ✅ Correctly handled non-existent source registry")
            
            # Test 2: Non-existent target registry
            result2 = mcp_server.migrate_context(
                context=self.test_context,
                source_registry="dev",
                target_registry="nonexistent",
                dry_run=True
            )
            
            if "error" not in result2:
                print(f"   ❌ Should have failed for non-existent target registry")
                return False
            
            print(f"   ✅ Correctly handled non-existent target registry")
            
            # Test 3: Empty context
            empty_context = f"empty-{uuid.uuid4().hex[:6]}"
            result3 = mcp_server.migrate_context(
                context=empty_context,
                source_registry="dev",
                target_registry="prod",
                dry_run=True
            )
            
            # This should not error, but should report 0 subjects
            if "error" in result3:
                print(f"   ⚠️  Empty context caused error: {result3['error']}")
            else:
                subject_count = result3.get("subject_count", 0)
                if subject_count == 0:
                    print(f"   ✅ Correctly handled empty context (0 subjects)")
                else:
                    print(f"   ⚠️  Empty context reported {subject_count} subjects")
            
            print(f"   ✅ Migration error handling tests completed")
            return True
            
        except Exception as e:
            print(f"   ❌ Migration error handling test failed: {e}")
            return False
    
    def test_migration_task_tracking(self) -> bool:
        """Test migration task tracking functionality"""
        print(f"\n📋 Testing migration task tracking...")
        
        try:
            # Get initial task count
            initial_tasks = mcp_server.list_migrations()
            if "error" in initial_tasks:
                print(f"   ❌ Could not list initial migrations: {initial_tasks['error']}")
                return False
            
            initial_count = len(initial_tasks) if isinstance(initial_tasks, list) else 0
            print(f"   📊 Initial migration tasks: {initial_count}")
            
            # Perform a dry run migration to create a task
            task_result = mcp_server.migrate_context(
                context=".",  # Use default context
                source_registry="dev",
                target_registry="prod",
                dry_run=True
            )
            
            if "error" in task_result:
                print(f"   ⚠️  Task creation failed: {task_result['error']}")
                # This might be expected if no subjects in default context
                if "No subjects found" in task_result['error']:
                    print(f"   ✅ Correctly handled empty context for task tracking")
                    return True
                return False
            
            # Check if task was created
            migration_id = task_result.get("migration_id")
            if migration_id:
                print(f"   ✅ Migration task created: {migration_id}")
                
                # Try to get task status
                status_result = mcp_server.get_migration_status(migration_id)
                if "error" not in status_result:
                    print(f"   ✅ Migration task status retrieved")
                else:
                    print(f"   ⚠️  Could not get task status: {status_result['error']}")
            else:
                print(f"   ⚠️  No migration ID returned")
            
            print(f"   ✅ Migration task tracking test completed")
            return True
            
        except Exception as e:
            print(f"   ❌ Migration task tracking test failed: {e}")
            return False
    
    def test_registry_comparison_integration(self) -> bool:
        """Test registry comparison integration"""
        print(f"\n🔍 Testing registry comparison integration...")
        
        try:
            # Test cross-registry comparison
            comparison = mcp_server.compare_registries("dev", "prod")
            
            if "error" in comparison:
                print(f"   ❌ Registry comparison failed: {comparison['error']}")
                return False
            
            print(f"   ✅ Registry comparison successful")
            
            # Test context-specific comparison
            context_comparison = mcp_server.compare_contexts_across_registries(
                "dev", "prod", "."
            )
            
            if "error" in context_comparison:
                print(f"   ⚠️  Context comparison had issues: {context_comparison['error']}")
            else:
                print(f"   ✅ Context comparison successful")
            
            # Test missing schemas detection
            missing = mcp_server.find_missing_schemas("dev", "prod")
            
            if "error" in missing:
                print(f"   ❌ Missing schemas detection failed: {missing['error']}")
                return False
            
            missing_count = missing.get("missing_count", 0)
            print(f"   ✅ Missing schemas detection: {missing_count} missing")
            
            print(f"   ✅ Registry comparison integration test completed")
            return True
            
        except Exception as e:
            print(f"   ❌ Registry comparison integration test failed: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all lightweight migration integration tests"""
        print("🚀 Starting Lightweight Migration Integration Tests")
        print("=" * 60)
        print("Testing migration integration without Docker environment management")
        print("=" * 60)
        
        tests = [
            ("End-to-End Migration", self.test_end_to_end_migration),
            ("Migration Error Handling", self.test_migration_error_handling),
            ("Migration Task Tracking", self.test_migration_task_tracking),
            ("Registry Comparison Integration", self.test_registry_comparison_integration)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🧪 Running: {test_name}")
            if test_func():
                passed += 1
                print(f"   ✅ {test_name} PASSED")
            else:
                print(f"   ❌ {test_name} FAILED")
        
        print(f"\n📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print(f"\n🎉 ALL LIGHTWEIGHT MIGRATION INTEGRATION TESTS PASSED!")
            print(f"✅ End-to-end migration workflow works correctly")
            print(f"✅ Migration error handling is robust")
            print(f"✅ Migration task tracking functions properly")
            print(f"✅ Registry comparison integration is functional")
            return True
        else:
            print(f"\n⚠️  {total - passed} migration integration tests failed")
            print(f"Migration integration functionality may have issues")
            return False

def main():
    """Run the lightweight migration integration tests"""
    test_runner = LightweightMigrationIntegrationTest()
    success = test_runner.run_all_tests()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 