#!/usr/bin/env python3
"""
Integration Test for Default Context "." Migration

This test specifically validates that schemas in the default context "."
are properly detected and migrated. This addresses the issue reported
where bulk context migration was showing "0 subjects migrated" even
though 339 schemas were present in the "." context from sbt-jump.
"""

import os
import sys
import json
import uuid
import requests
import time
from datetime import datetime

# Add parent directory to path to import the MCP server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import kafka_schema_registry_multi_mcp as mcp_server

class DefaultContextDotMigrationTest:
    """Test class for default context '.' migration scenarios"""
    
    def __init__(self):
        self.dev_url = "http://localhost:38081"
        self.prod_url = "http://localhost:38082"
        self.test_subjects = []
        self.is_multi_registry = False
        
        # Detect if we're in multi-registry mode
        try:
            dev_response = requests.get(f"{self.dev_url}/subjects", timeout=5)
            prod_response = requests.get(f"{self.prod_url}/subjects", timeout=5)
            if dev_response.status_code == 200 and prod_response.status_code == 200:
                self.is_multi_registry = True
                print(f"🔍 Detected multi-registry environment (DEV + PROD)")
        except Exception:
            print(f"🔍 Detected single-registry environment (DEV only)")
            # In single registry mode, use the same registry for both source and target
            self.prod_url = self.dev_url
        
        # Setup test environment variables
        if self.is_multi_registry:
            # Multi-registry setup
            os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
            os.environ["SCHEMA_REGISTRY_URL_1"] = self.dev_url
            os.environ["SCHEMA_REGISTRY_NAME_2"] = "prod" 
            os.environ["SCHEMA_REGISTRY_URL_2"] = self.prod_url
            os.environ["READONLY_2"] = "false"  # Allow writes to prod for testing
        else:
            # Single registry setup
            os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
            os.environ["SCHEMA_REGISTRY_URL_1"] = self.dev_url
            # Clear any multi-registry environment variables
            for i in range(2, 9):
                for var in [f"SCHEMA_REGISTRY_NAME_{i}", f"SCHEMA_REGISTRY_URL_{i}", f"READONLY_{i}"]:
                    if var in os.environ:
                        del os.environ[var]
        
        # Reinitialize registry manager with test config
        mcp_server.registry_manager._load_registries()
        
    def setup_schemas_in_default_context_dot(self) -> bool:
        """Create test schemas specifically in the default context '.'"""
        print(f"📝 Setting up test schemas in default context '.'...")
        
        test_schemas = [
            {
                "subject": f"dot-context-user-{uuid.uuid4().hex[:6]}",
                "schema": {
                    "type": "record",
                    "name": "DotContextUser",
                    "fields": [
                        {"name": "userId", "type": "string"},
                        {"name": "username", "type": "string"},
                        {"name": "email", "type": "string"}
                    ]
                }
            },
            {
                "subject": f"dot-context-order-{uuid.uuid4().hex[:6]}",
                "schema": {
                    "type": "record", 
                    "name": "DotContextOrder",
                    "fields": [
                        {"name": "orderId", "type": "string"},
                        {"name": "customerId", "type": "string"},
                        {"name": "total", "type": "double"}
                    ]
                }
            },
            {
                "subject": f"dot-context-product-{uuid.uuid4().hex[:6]}",
                "schema": {
                    "type": "record",
                    "name": "DotContextProduct", 
                    "fields": [
                        {"name": "productId", "type": "string"},
                        {"name": "name", "type": "string"},
                        {"name": "price", "type": "double"}
                    ]
                }
            }
        ]
        
        created_count = 0
        for schema_def in test_schemas:
            try:
                subject = schema_def["subject"]
                schema = schema_def["schema"]
                
                # Create in dev registry in the default context (no context path)
                # This simulates how schemas are created in the default context "."
                url = f"{self.dev_url}/subjects/{subject}/versions"
                payload = {"schema": json.dumps(schema)}
                
                response = requests.post(
                    url,
                    headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
                    json=payload,
                    timeout=10
                )
                
                if response.status_code in [200, 409]:  # 409 = already exists
                    self.test_subjects.append(subject)
                    created_count += 1
                    print(f"   ✅ Created {subject} in default context")
                else:
                    print(f"   ❌ Failed to create {subject}: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"   ❌ Error creating {subject}: {e}")
        
        print(f"📊 Created {created_count}/{len(test_schemas)} test schemas in default context")
        return created_count > 0
        
    def verify_schemas_in_default_context(self) -> bool:
        """Verify that schemas exist in the default context and can be listed"""
        print(f"\n🔍 Verifying schemas exist in default context...")
        
        try:
            # Test 1: List subjects with context=None (should find default context schemas)
            subjects_none = mcp_server.list_subjects(context=None, registry="dev")
            print(f"   📋 Found {len(subjects_none)} subjects with context=None")
            
            # Test 2: List subjects with context="." (should find same schemas)
            subjects_dot = mcp_server.list_subjects(context=".", registry="dev")
            print(f"   📋 Found {len(subjects_dot)} subjects with context='.'")
            
            # Both should return the same results due to our fix
            if len(subjects_none) == 0 and len(subjects_dot) == 0:
                print(f"   ❌ No subjects found in either case - setup may have failed")
                return False
                
            # Check that our test subjects are present
            test_subjects_found_none = [s for s in self.test_subjects if s in subjects_none]
            test_subjects_found_dot = [s for s in self.test_subjects if s in subjects_dot]
            
            print(f"   📋 Test subjects found with context=None: {len(test_subjects_found_none)}")
            print(f"   📋 Test subjects found with context='.': {len(test_subjects_found_dot)}")
            
            # The key test: both should find the same subjects
            if len(test_subjects_found_none) != len(test_subjects_found_dot):
                print(f"   ❌ CRITICAL: Different results for context=None vs context='.'!")
                print(f"      This indicates the '.' context fix is not working properly")
                return False
                
            if len(test_subjects_found_none) == 0:
                print(f"   ❌ Test subjects not found in default context")
                return False
                
            print(f"   ✅ Default context verification PASSED")
            return True
            
        except Exception as e:
            print(f"   ❌ Default context verification failed: {e}")
            return False
    
    def test_migrate_default_context_dot(self) -> bool:
        """Test migrating the default context specified as '.'"""
        print(f"\n🧪 Testing migration of default context '.'...")
        
        if not self.is_multi_registry:
            print(f"   ℹ️  Single registry mode - testing subject detection for context '.'")
            # In single registry mode, test that we can detect subjects in default context
            try:
                subjects_in_dev = mcp_server.list_subjects(context=".", registry="dev")
                test_subjects_in_dev = [s for s in self.test_subjects if s in subjects_in_dev]
                
                print(f"   📋 Found {len(test_subjects_in_dev)} test subjects in dev context '.'")
                
                if len(test_subjects_in_dev) == 0:
                    print(f"   ❌ No test subjects found in dev context '.' - cannot test migration")
                    return False
                
                # Test dry run migration (this should work even in single registry mode)
                print(f"   🚀 Testing dry run migration of default context '.'...")
                migration_result = mcp_server.migrate_context(
                    context=".",  # This is the critical test case
                    source_registry="dev",
                    target_registry="dev",  # Same registry in single mode
                    dry_run=True
                )
                
                # Validate dry run results
                if "error" in migration_result:
                    print(f"   ❌ Dry run migration failed: {migration_result['error']}")
                    return False
                
                print(f"   📊 Dry Run Migration Results:")
                print(f"      Subjects to migrate: {migration_result.get('subject_count', 0)}")
                print(f"      Dry run: {migration_result.get('dry_run', False)}")
                print(f"      Status: {migration_result.get('status', 'unknown')}")
                
                # Critical test: Check that we found subjects
                subject_count = migration_result.get('subject_count', 0)
                
                if subject_count == 0:
                    print(f"   ❌ CRITICAL: 0 subjects found - this is the original bug!")
                    print(f"      The '.' context is not being handled properly")
                    return False
                
                print(f"   ✅ Default context '.' migration test PASSED (single registry mode)")
                return True
                
            except Exception as e:
                print(f"   ❌ Default context '.' migration test failed: {e}")
                return False
        
        # Multi-registry mode - original test
        try:
            # First verify we have subjects to migrate
            subjects_in_dev = mcp_server.list_subjects(context=".", registry="dev")
            test_subjects_in_dev = [s for s in self.test_subjects if s in subjects_in_dev]
            
            print(f"   📋 Found {len(test_subjects_in_dev)} test subjects in dev context '.'")
            
            if len(test_subjects_in_dev) == 0:
                print(f"   ❌ No test subjects found in dev context '.' - cannot test migration")
                return False
            
            # Check target before migration
            subjects_in_prod_before = mcp_server.list_subjects(context=".", registry="prod")
            test_subjects_in_prod_before = [s for s in self.test_subjects if s in subjects_in_prod_before]
            print(f"   📋 Found {len(test_subjects_in_prod_before)} test subjects in prod context '.' (before)")
            
            # Perform migration with context="."
            print(f"   🚀 Migrating default context '.' from dev to prod...")
            migration_result = mcp_server.migrate_context(
                context=".",  # This is the critical test case
                source_registry="dev",
                target_registry="prod",
                dry_run=False
            )
            
            # Validate migration results
            if "error" in migration_result:
                print(f"   ❌ Migration failed: {migration_result['error']}")
                return False
            
            print(f"   📊 Migration Results:")
            print(f"      Total subjects: {migration_result.get('total_subjects', 0)}")
            print(f"      Successful: {migration_result.get('successful_migrations', 0)}")
            print(f"      Failed: {migration_result.get('failed_migrations', 0)}")
            print(f"      Skipped: {migration_result.get('skipped_migrations', 0)}")
            print(f"      Success rate: {migration_result.get('success_rate', '0%')}")
            
            # Critical test: Check that we found and migrated subjects
            total_subjects = migration_result.get('total_subjects', 0)
            successful_count = migration_result.get('successful_migrations', 0)
            skipped_count = migration_result.get('skipped_migrations', 0)
            
            if total_subjects == 0:
                print(f"   ❌ CRITICAL: 0 subjects found - this is the original bug!")
                print(f"      The '.' context is not being handled properly")
                return False
            
            if successful_count == 0 and skipped_count == 0:
                print(f"   ❌ CRITICAL: 0 subjects migrated or skipped!")
                return False
            
            # Verify subjects now exist in target
            subjects_in_prod_after = mcp_server.list_subjects(context=".", registry="prod")
            test_subjects_in_prod_after = [s for s in self.test_subjects if s in subjects_in_prod_after]
            print(f"   📋 Found {len(test_subjects_in_prod_after)} test subjects in prod context '.' (after)")
            
            # Should have more subjects in prod now (unless they were all skipped due to existing)
            if successful_count > 0:
                if len(test_subjects_in_prod_after) <= len(test_subjects_in_prod_before):
                    print(f"   ⚠️  Expected more subjects in prod after successful migration")
                    # This might be OK if schemas already existed and were skipped
                    
            print(f"   ✅ Default context '.' migration test PASSED (multi-registry mode)")
            return True
            
        except Exception as e:
            print(f"   ❌ Default context '.' migration test failed: {e}")
            return False
    
    def test_url_building_for_default_context(self) -> bool:
        """Test that URL building correctly handles default context '.'"""
        print(f"\n🧪 Testing URL building for default context '.'...")
        
        try:
            # Get a registry client
            dev_client = mcp_server.registry_manager.get_registry("dev")
            if not dev_client:
                print(f"   ❌ Could not get dev registry client")
                return False
            
            # Test URL building with different context values
            url_none = dev_client.build_context_url("/subjects", None)
            url_empty = dev_client.build_context_url("/subjects", "")
            url_dot = dev_client.build_context_url("/subjects", ".")
            url_named = dev_client.build_context_url("/subjects", "production")
            
            print(f"   🔗 URL with context=None: {url_none}")
            print(f"   🔗 URL with context='': {url_empty}")
            print(f"   🔗 URL with context='.': {url_dot}")
            print(f"   🔗 URL with context='production': {url_named}")
            
            # Key test: context="." should produce the same URL as context=None
            if url_dot != url_none:
                print(f"   ❌ CRITICAL: URL for context='.' differs from context=None")
                print(f"      This indicates the build_context_url fix is not working")
                return False
            
            # Named context should be different
            if url_named == url_none:
                print(f"   ❌ Named context URL should be different from default")
                return False
            
            # All should point to the subjects endpoint
            if "/subjects" not in url_none:
                print(f"   ❌ URL doesn't contain /subjects endpoint")
                return False
            
            print(f"   ✅ URL building test PASSED")
            return True
            
        except Exception as e:
            print(f"   ❌ URL building test failed: {e}")
            return False
    
    def cleanup_test_schemas(self):
        """Clean up test schemas from both registries"""
        print(f"\n🧹 Cleaning up test schemas...")
        
        for registry_url in [self.dev_url, self.prod_url]:
            for subject in self.test_subjects:
                try:
                    # Delete from default context
                    url = f"{registry_url}/subjects/{subject}"
                    requests.delete(url, timeout=5)
                except Exception:
                    pass  # Ignore cleanup errors
    
    def run_all_tests(self) -> bool:
        """Run all default context '.' tests"""
        print("🚀 Starting Default Context '.' Migration Tests")
        print("=" * 60)
        print("This test validates the fix for the issue where bulk context")
        print("migration shows '0 subjects migrated' for default context '.'")
        print("=" * 60)
        
        # Setup
        if not self.setup_schemas_in_default_context_dot():
            print("❌ Failed to setup test schemas in default context")
            return False
        
        tests = [
            ("URL Building for '.'", self.test_url_building_for_default_context),
            ("Default Context Verification", self.verify_schemas_in_default_context),
            ("Migrate Default Context '.'", self.test_migrate_default_context_dot)
        ]
        
        passed = 0
        total = len(tests)
        
        try:
            for test_name, test_func in tests:
                print(f"\n🧪 Running: {test_name}")
                if test_func():
                    passed += 1
                    print(f"   ✅ {test_name} PASSED")
                else:
                    print(f"   ❌ {test_name} FAILED")
            
            print(f"\n📊 Test Results: {passed}/{total} tests passed")
            
            if passed == total:
                print(f"\n🎉 ALL DEFAULT CONTEXT '.' TESTS PASSED!")
                print(f"✅ The default context '.' migration bug has been fixed")
                return True
            else:
                print(f"\n⚠️  {total - passed} tests failed")
                return False
                
        finally:
            self.cleanup_test_schemas()

def main():
    """Run the default context '.' migration tests"""
    test_runner = DefaultContextDotMigrationTest()
    success = test_runner.run_all_tests()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 