#!/usr/bin/env python3
"""
Lightweight Migration Tests

This test validates migration functionality using the existing
multi-registry environment without requiring additional setup.
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

class LightweightMigrationTest:
    """Lightweight test class for migration functionality"""
    
    def __init__(self):
        self.dev_url = "http://localhost:38081"
        self.prod_url = "http://localhost:38082"
        
        # Setup environment for multi-registry mode
        os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
        os.environ["SCHEMA_REGISTRY_URL_1"] = self.dev_url
        os.environ["READONLY_1"] = "false"
        
        os.environ["SCHEMA_REGISTRY_NAME_2"] = "prod"
        os.environ["SCHEMA_REGISTRY_URL_2"] = self.prod_url
        os.environ["READONLY_2"] = "false"  # Allow writes for testing
        
        # Clear any other registry configurations
        for i in range(3, 9):
            for var in [f"SCHEMA_REGISTRY_NAME_{i}", f"SCHEMA_REGISTRY_URL_{i}", f"READONLY_{i}"]:
                if var in os.environ:
                    del os.environ[var]
        
        # Reinitialize registry manager with multi-registry config
        mcp_server.registry_manager._load_registries()
    
    def test_default_context_url_building(self) -> bool:
        """Test that default context '.' URL building works correctly"""
        print(f"\n🔗 Testing default context URL building...")
        
        try:
            # Get client
            client = mcp_server.registry_manager.get_registry("dev")
            if not client:
                print(f"   ❌ Could not get DEV registry client")
                return False
            
            # Test URL building with different context values
            url_none = client.build_context_url("/subjects", None)
            url_dot = client.build_context_url("/subjects", ".")
            url_empty = client.build_context_url("/subjects", "")
            url_production = client.build_context_url("/subjects", "production")
            
            print(f"   📊 URL Building Results:")
            print(f"      context=None: {url_none}")
            print(f"      context='.': {url_dot}")
            print(f"      context='': {url_empty}")
            print(f"      context='production': {url_production}")
            
            # Verify the fix: context='.' should be treated like None
            if url_none != url_dot:
                print(f"   ❌ FAILURE: context=None and context='.' produce different URLs")
                return False
            
            # Verify that production context is different
            if url_none == url_production:
                print(f"   ❌ FAILURE: default context URL same as production context URL")
                return False
            
            print(f"   ✅ Default context URL building is correct")
            return True
            
        except Exception as e:
            print(f"   ❌ Default context URL building test failed: {e}")
            return False
    
    def test_dry_run_migration(self) -> bool:
        """Test dry run migration functionality"""
        print(f"\n🧪 Testing dry run migration...")
        
        try:
            # Test dry run migration for default context
            migration_result = mcp_server.migrate_context(
                context=".",
                source_registry="dev",
                target_registry="prod",
                dry_run=True
            )
            
            if "error" in migration_result:
                print(f"   ❌ Dry run migration failed: {migration_result['error']}")
                return False
            
            if not migration_result.get("dry_run", False):
                print(f"   ❌ Migration result not marked as dry run")
                return False
            
            print(f"   ✅ Dry run migration successful")
            print(f"      Status: {migration_result.get('status', 'unknown')}")
            print(f"      Subjects found: {migration_result.get('subject_count', 0)}")
            print(f"      Versions to migrate: {migration_result.get('total_versions_to_migrate', 0)}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Dry run migration test failed: {e}")
            return False
    
    def test_registry_comparison(self) -> bool:
        """Test registry comparison functionality"""
        print(f"\n📊 Testing registry comparison...")
        
        try:
            # Compare dev and prod registries
            comparison = mcp_server.compare_registries("dev", "prod")
            
            if "error" in comparison:
                print(f"   ❌ Registry comparison failed: {comparison['error']}")
                return False
            
            print(f"   ✅ Registry comparison successful")
            
            subjects_info = comparison.get('subjects', {})
            if subjects_info:
                source_total = subjects_info.get('source_total', 0)
                target_total = subjects_info.get('target_total', 0)
                common = len(subjects_info.get('common', []))
                source_only = len(subjects_info.get('source_only', []))
                target_only = len(subjects_info.get('target_only', []))
                
                print(f"      📈 Comparison Results:")
                print(f"         DEV subjects: {source_total}")
                print(f"         PROD subjects: {target_total}")
                print(f"         Common: {common}")
                print(f"         DEV only: {source_only}")
                print(f"         PROD only: {target_only}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Registry comparison test failed: {e}")
            return False
    
    def test_migration_tools_availability(self) -> bool:
        """Test that migration tools are available and working"""
        print(f"\n🛠️  Testing migration tools availability...")
        
        try:
            # Test find_missing_schemas
            missing_schemas = mcp_server.find_missing_schemas("dev", "prod")
            
            if "error" in missing_schemas:
                print(f"   ❌ find_missing_schemas failed: {missing_schemas['error']}")
                return False
            
            print(f"   ✅ find_missing_schemas working")
            print(f"      Missing schemas: {missing_schemas.get('missing_count', 0)}")
            
            # Test compare_contexts_across_registries (if contexts exist)
            try:
                context_comparison = mcp_server.compare_contexts_across_registries("dev", "prod", ".")
                
                if "error" not in context_comparison:
                    print(f"   ✅ compare_contexts_across_registries working")
                    subjects_info = context_comparison.get('subjects', {})
                    if subjects_info:
                        print(f"      Default context - DEV: {subjects_info.get('source_total', 0)}, PROD: {subjects_info.get('target_total', 0)}")
                else:
                    print(f"   ⚠️  compare_contexts_across_registries: {context_comparison['error']}")
            except Exception as e:
                print(f"   ⚠️  compare_contexts_across_registries error: {e}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Migration tools availability test failed: {e}")
            return False
    
    def test_id_preservation_dry_run(self) -> bool:
        """Test ID preservation functionality in dry run mode"""
        print(f"\n🆔 Testing ID preservation dry run...")
        
        try:
            # Test ID preservation dry run
            migration_result = mcp_server.migrate_context(
                context=".",
                source_registry="dev",
                target_registry="prod",
                preserve_ids=True,
                dry_run=True
            )
            
            if "error" in migration_result:
                print(f"   ❌ ID preservation dry run failed: {migration_result['error']}")
                return False
            
            preserve_ids = migration_result.get("preserve_ids", False)
            is_dry_run = migration_result.get("dry_run", False)
            
            if not is_dry_run:
                print(f"   ❌ Migration not marked as dry run")
                return False
            
            if not preserve_ids:
                print(f"   ❌ Migration not marked for ID preservation")
                return False
            
            print(f"   ✅ ID preservation dry run successful")
            print(f"      Status: {migration_result.get('status', 'unknown')}")
            print(f"      Preserve IDs: {preserve_ids}")
            print(f"      Dry Run: {is_dry_run}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ ID preservation dry run test failed: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all lightweight migration tests"""
        print("🚀 Starting Lightweight Migration Tests")
        print("=" * 60)
        print("Testing migration functionality with existing environment")
        print("=" * 60)
        
        tests = [
            ("Default Context URL Building", self.test_default_context_url_building),
            ("Dry Run Migration", self.test_dry_run_migration),
            ("Registry Comparison", self.test_registry_comparison),
            ("Migration Tools Availability", self.test_migration_tools_availability),
            ("ID Preservation Dry Run", self.test_id_preservation_dry_run)
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
            print(f"\n🎉 ALL LIGHTWEIGHT MIGRATION TESTS PASSED!")
            print(f"✅ Default context '.' URL building works correctly")
            print(f"✅ Dry run migration functionality is working")
            print(f"✅ Registry comparison tools are functional") 
            print(f"✅ Migration tools are available and working")
            print(f"✅ ID preservation functionality is available")
            return True
        else:
            print(f"\n⚠️  {total - passed} migration tests failed")
            print(f"Some migration functionality may have issues")
            return False

def main():
    """Run the lightweight migration tests"""
    test_runner = LightweightMigrationTest()
    success = test_runner.run_all_tests()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 