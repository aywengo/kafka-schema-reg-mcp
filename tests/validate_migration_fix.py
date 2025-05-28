#!/usr/bin/env python3
"""
Simple validation script for the migration integration fix

This script tests the migration functionality with simplified settings
to validate that the fix works correctly.
"""

import os
import sys
import uuid

# Add parent directory to path to import the MCP server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("🔧 Validating Migration Integration Fix")
    print("=" * 50)
    
    # Setup environment for multi-registry mode
    os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
    os.environ["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
    os.environ["READONLY_1"] = "false"
    
    os.environ["SCHEMA_REGISTRY_NAME_2"] = "prod"
    os.environ["SCHEMA_REGISTRY_URL_2"] = "http://localhost:38082"
    os.environ["READONLY_2"] = "false"
    
    # Clear global READONLY
    if "READONLY" in os.environ:
        del os.environ["READONLY"]
    
    try:
        import kafka_schema_registry_multi_mcp as mcp_server
        
        # Force reload configuration
        mcp_server.registry_manager._load_registries()
        
        print("✅ Multi-registry server loaded")
        
        # Test context
        test_context = f"validation-{uuid.uuid4().hex[:8]}"
        print(f"🧪 Using test context: {test_context}")
        
        # Step 1: Create a test schema in DEV
        test_subject = f"test-schema-{uuid.uuid4().hex[:6]}"
        test_schema = {
            "type": "record",
            "name": "ValidationEvent",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "timestamp", "type": "long"}
            ]
        }
        
        print(f"📝 Creating test schema: {test_subject}")
        create_result = mcp_server.register_schema(
            subject=test_subject,
            schema_definition=test_schema,
            context=test_context,
            registry="dev"
        )
        
        if "error" in create_result:
            print(f"❌ Failed to create schema: {create_result['error']}")
            return False
        
        print(f"✅ Schema created with ID: {create_result.get('id')}")
        
        # Step 2: Verify schema exists in DEV
        dev_subjects = mcp_server.list_subjects(context=test_context, registry="dev")
        expected_subject = f":.{test_context}:{test_subject}"
        
        if expected_subject not in dev_subjects:
            print(f"❌ Schema not found in DEV: {dev_subjects}")
            return False
        
        print(f"✅ Schema found in DEV with context prefix")
        
        # Step 3: Perform migration with simplified settings
        print(f"🚀 Testing migration with simplified settings...")
        migration_result = mcp_server.migrate_context(
            context=test_context,
            source_registry="dev",
            target_registry="prod",
            migrate_all_versions=False,  # Only latest version
            preserve_ids=False,         # No ID preservation
            dry_run=False
        )
        
        if "error" in migration_result:
            print(f"❌ Migration failed: {migration_result['error']}")
            return False
        
        successful_migrations = migration_result.get("successful_migrations", 0)
        total_subjects = migration_result.get("total_subjects", 0)
        
        print(f"📊 Migration result: {successful_migrations}/{total_subjects} subjects")
        
        if successful_migrations == 0:
            print(f"❌ No subjects migrated!")
            
            # Show detailed error info
            if "results" in migration_result:
                results = migration_result["results"]
                version_details = results.get('version_details', [])
                for detail in version_details:
                    if detail.get('status') == 'failed':
                        error = detail.get('error', 'no details')
                        print(f"   Error: {error}")
            
            return False
        
        print(f"✅ Migration successful!")
        
        # Step 4: Verify schema exists in PROD
        prod_subjects = mcp_server.list_subjects(context=test_context, registry="prod")
        
        if expected_subject not in prod_subjects:
            print(f"❌ Schema not found in PROD after migration: {prod_subjects}")
            return False
        
        print(f"✅ Schema found in PROD after migration")
        
        print(f"\n🎉 Migration integration fix validation PASSED!")
        print(f"✅ Schema creation works")
        print(f"✅ Context prefixing works")
        print(f"✅ Migration works with simplified settings")
        print(f"✅ Cross-registry migration successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        try:
            import requests
            for registry_url in ["http://localhost:38081", "http://localhost:38082"]:
                try:
                    requests.delete(f"{registry_url}/contexts/{test_context}", timeout=5)
                except Exception:
                    pass
        except Exception:
            pass

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 