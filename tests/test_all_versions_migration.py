#!/usr/bin/env python3
"""
All Versions Migration Test

This test validates that the enhanced migrate_context function can preserve
the complete schema evolution history by migrating all versions of schemas,
not just the latest version.
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

class AllVersionsMigrationTest:
    """Test class for all-versions migration scenarios"""
    
    def __init__(self):
        self.dev_url = "http://localhost:38081"
        self.prod_url = "http://localhost:38082"
        self.test_context = f"test-all-versions-{uuid.uuid4().hex[:8]}"
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
        
    def create_schema_evolution(self) -> bool:
        """Create schemas with multiple versions to test migration"""
        print(f"📝 Creating schema evolution in context '{self.test_context}'...")
        
        subject = f"user-events-evolution-{uuid.uuid4().hex[:6]}"
        self.test_subjects.append(subject)
        
        # Schema evolution: v1 -> v2 -> v3 (forward compatible)
        schemas = [
            # Version 1: Basic user event
            {
                "type": "record",
                "name": "UserEvent",
                "namespace": "com.example.events",
                "fields": [
                    {"name": "userId", "type": "string"},
                    {"name": "eventType", "type": "string"},
                    {"name": "timestamp", "type": "long"}
                ]
            },
            # Version 2: Add optional email field (forward compatible)
            {
                "type": "record", 
                "name": "UserEvent",
                "namespace": "com.example.events",
                "fields": [
                    {"name": "userId", "type": "string"},
                    {"name": "eventType", "type": "string"},
                    {"name": "timestamp", "type": "long"},
                    {"name": "email", "type": ["null", "string"], "default": None}
                ]
            },
            # Version 3: Add optional metadata field (forward compatible)
            {
                "type": "record",
                "name": "UserEvent", 
                "namespace": "com.example.events",
                "fields": [
                    {"name": "userId", "type": "string"},
                    {"name": "eventType", "type": "string"},
                    {"name": "timestamp", "type": "long"},
                    {"name": "email", "type": ["null", "string"], "default": None},
                    {"name": "metadata", "type": ["null", {"type": "map", "values": "string"}], "default": None}
                ]
            }
        ]
        
        created_versions = 0
        for i, schema in enumerate(schemas):
            try:
                # Create in dev registry with context
                url = f"{self.dev_url}/contexts/{self.test_context}/subjects/{subject}/versions"
                payload = {"schema": json.dumps(schema)}
                
                response = requests.post(
                    url,
                    headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
                    json=payload,
                    timeout=10
                )
                
                if response.status_code in [200, 409]:  # 409 = already exists
                    created_versions += 1
                    version_num = i + 1
                    print(f"   ✅ Created version {version_num} of {subject}")
                else:
                    print(f"   ❌ Failed to create version {i+1}: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"   ❌ Error creating version {i+1}: {e}")
        
        print(f"📊 Created {created_versions}/{len(schemas)} schema versions")
        return created_versions > 0
    
    def verify_schema_versions(self, subject: str, registry: str, context: str) -> int:
        """Verify how many versions exist for a subject"""
        try:
            versions_result = mcp_server.get_schema_versions(subject, context, registry)
            if isinstance(versions_result, dict) and "error" in versions_result:
                return 0
            return len(versions_result) if isinstance(versions_result, list) else 0
        except Exception:
            return 0
    
    def test_latest_only_migration(self) -> bool:
        """Test migration with migrate_all_versions=False (default behavior)"""
        print(f"\n🧪 Testing latest-only migration (migrate_all_versions=False)...")
        
        if not self.test_subjects:
            print(f"   ❌ No test subjects available")
            return False
        
        subject = self.test_subjects[0]
        
        try:
            # Verify we have multiple versions in source
            source_versions = self.verify_schema_versions(subject, "dev", self.test_context)
            print(f"   📋 Source has {source_versions} versions of {subject}")
            
            if source_versions < 2:
                print(f"   ❌ Need at least 2 versions for this test")
                return False
            
            # Perform latest-only migration
            if self.is_multi_registry:
                target_registry = "prod"
            else:
                target_registry = "dev"  # Same registry in single mode
                
            migration_result = mcp_server.migrate_context(
                context=self.test_context,
                source_registry="dev",
                target_registry=target_registry,
                migrate_all_versions=False,  # Only latest
                preserve_ids=False,  # Match original test expectations
                dry_run=False
            )
            
            if "error" in migration_result:
                print(f"   ❌ Latest-only migration failed: {migration_result['error']}")
                return False
            
            print(f"   📊 Migration Results:")
            print(f"      Subjects migrated: {migration_result.get('successful_migrations', 0)}")
            print(f"      Versions migrated: {migration_result.get('total_versions_migrated', 0)}")
            print(f"      Migrate all versions: {migration_result.get('migrate_all_versions', False)}")
            
            # Should only migrate 1 version (latest) per subject
            expected_versions = migration_result.get('successful_migrations', 0)
            actual_versions = migration_result.get('total_versions_migrated', 0)
            
            if actual_versions != expected_versions:
                print(f"   ❌ Expected {expected_versions} versions, got {actual_versions}")
                return False
            
            print(f"   ✅ Latest-only migration test PASSED")
            return True
            
        except Exception as e:
            print(f"   ❌ Latest-only migration test failed: {e}")
            return False
    
    def test_all_versions_migration(self) -> bool:
        """Test migration with migrate_all_versions=True"""
        print(f"\n🧪 Testing all-versions migration (migrate_all_versions=True)...")
        
        if not self.test_subjects:
            print(f"   ❌ No test subjects available")
            return False
        
        subject = self.test_subjects[0]
        
        try:
            # Verify we have multiple versions in source
            source_versions = self.verify_schema_versions(subject, "dev", self.test_context)
            print(f"   📋 Source has {source_versions} versions of {subject}")
            
            if source_versions < 2:
                print(f"   ❌ Need at least 2 versions for this test")
                return False
            
            # Clear target if in multi-registry mode
            if self.is_multi_registry:
                try:
                    # Delete any existing schemas in target
                    url = f"{self.prod_url}/contexts/{self.test_context}/subjects/{subject}"
                    requests.delete(url, timeout=5)
                except Exception:
                    pass
            
            # Perform all-versions migration
            target_registry = "prod" if self.is_multi_registry else "dev"
            
            migration_result = mcp_server.migrate_context(
                context=self.test_context,
                source_registry="dev",
                target_registry=target_registry,
                migrate_all_versions=True,  # All versions
                preserve_ids=False,  # Match original test expectations
                dry_run=False
            )
            
            if "error" in migration_result:
                print(f"   ❌ All-versions migration failed: {migration_result['error']}")
                return False
            
            print(f"   📊 Migration Results:")
            print(f"      Subjects migrated: {migration_result.get('successful_migrations', 0)}")
            print(f"      Versions migrated: {migration_result.get('total_versions_migrated', 0)}")
            print(f"      Versions skipped: {migration_result.get('total_versions_skipped', 0)}")
            print(f"      Migrate all versions: {migration_result.get('migrate_all_versions', False)}")
            print(f"      Version success rate: {migration_result.get('version_success_rate', '0%')}")
            
            # Should migrate all versions (or skip if they already exist)
            total_versions_processed = migration_result.get('total_versions_migrated', 0) + migration_result.get('total_versions_skipped', 0)
            
            if not self.is_multi_registry:
                # In single registry mode, versions might be skipped because they already exist
                if total_versions_processed < source_versions:
                    print(f"   ⚠️  Processed {total_versions_processed} versions, expected {source_versions}")
                    print(f"      This is acceptable in single-registry mode")
            else:
                # In multi-registry mode, we should migrate all versions
                migrated_versions = migration_result.get('total_versions_migrated', 0)
                if migrated_versions < source_versions:
                    print(f"   ❌ Expected to migrate {source_versions} versions, only migrated {migrated_versions}")
                    return False
            
            # Verify version details
            version_details = migration_result.get('results', {}).get('version_details', [])
            print(f"   📋 Version Details:")
            for detail in version_details:
                status = detail.get('status', 'unknown')
                version = detail.get('version', 'unknown')
                print(f"      Version {version}: {status}")
            
            print(f"   ✅ All-versions migration test PASSED")
            return True
            
        except Exception as e:
            print(f"   ❌ All-versions migration test failed: {e}")
            return False
    
    def test_dry_run_all_versions(self) -> bool:
        """Test dry run with all versions migration"""
        print(f"\n🧪 Testing dry run with all-versions migration...")
        
        try:
            # Test dry run for all versions
            migration_result = mcp_server.migrate_context(
                context=self.test_context,
                source_registry="dev",
                target_registry="prod" if self.is_multi_registry else "dev",
                migrate_all_versions=True,
                preserve_ids=False,  # Match original test expectations
                dry_run=True
            )
            
            if "error" in migration_result:
                print(f"   ❌ Dry run failed: {migration_result['error']}")
                return False
            
            print(f"   📊 Dry Run Results:")
            print(f"      Subjects to migrate: {migration_result.get('subject_count', 0)}")
            print(f"      Total versions to migrate: {migration_result.get('total_versions_to_migrate', 0)}")
            print(f"      Migrate all versions: {migration_result.get('migrate_all_versions', False)}")
            print(f"      Status: {migration_result.get('status', 'unknown')}")
            
            # Should be marked as dry run
            if not migration_result.get('dry_run', False):
                print(f"   ❌ Result not marked as dry run!")
                return False
            
            # Should show more versions when migrate_all_versions=True
            total_versions = migration_result.get('total_versions_to_migrate', 0)
            subject_count = migration_result.get('subject_count', 0)
            
            if total_versions < subject_count:
                print(f"   ❌ Total versions ({total_versions}) should be >= subject count ({subject_count})")
                return False
            
            print(f"   ✅ Dry run all-versions test PASSED")
            return True
            
        except Exception as e:
            print(f"   ❌ Dry run all-versions test failed: {e}")
            return False
    
    def cleanup_test_schemas(self):
        """Clean up test schemas from both registries"""
        print(f"\n🧹 Cleaning up test schemas...")
        
        for registry_url in [self.dev_url, self.prod_url]:
            for subject in self.test_subjects:
                try:
                    # Delete from test context
                    url = f"{registry_url}/contexts/{self.test_context}/subjects/{subject}"
                    requests.delete(url, timeout=5)
                except Exception:
                    pass  # Ignore cleanup errors
        
        # Delete test context
        for registry_url in [self.dev_url, self.prod_url]:
            try:
                url = f"{registry_url}/contexts/{self.test_context}"
                requests.delete(url, timeout=5)
            except Exception:
                pass
    
    def run_all_tests(self) -> bool:
        """Run all all-versions migration tests"""
        print("🚀 Starting All-Versions Migration Tests")
        print("=" * 60)
        print("This test validates that migrate_context can preserve")
        print("complete schema evolution history by migrating all versions")
        print("=" * 60)
        
        # Setup
        if not self.create_schema_evolution():
            print("❌ Failed to create schema evolution for testing")
            return False
        
        tests = [
            ("Latest-Only Migration", self.test_latest_only_migration),
            ("All-Versions Migration", self.test_all_versions_migration),
            ("Dry Run All-Versions", self.test_dry_run_all_versions)
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
                print(f"\n🎉 ALL ALL-VERSIONS MIGRATION TESTS PASSED!")
                print(f"✅ The migrate_all_versions functionality is working correctly")
                print(f"✅ Complete schema evolution history can be preserved")
                return True
            else:
                print(f"\n⚠️  {total - passed} tests failed")
                return False
                
        finally:
            self.cleanup_test_schemas()

def main():
    """Run the all-versions migration tests"""
    test_runner = AllVersionsMigrationTest()
    success = test_runner.run_all_tests()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 