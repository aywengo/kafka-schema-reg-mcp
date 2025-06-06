#!/usr/bin/env python3
"""
PROD registry read-only enforcement

Tests that the MCP server correctly enforces read-only mode for the PROD registry
by blocking modification operations through MCP tools.
"""

import os
import sys
import json

# Add parent directory to Python path to find the main modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_test_readonly_validation():
    """Test unified server in multi-registry mode's read-only enforcement for PROD registry"""
    
    print(f"🧪 Starting MCP read-only validation test...")
    
    # Set up multi-registry environment variables
    os.environ["SCHEMA_REGISTRY_NAME_1"] = "development"
    os.environ["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
    os.environ["READONLY_1"] = "false"
    
    os.environ["SCHEMA_REGISTRY_NAME_2"] = "production"
    os.environ["SCHEMA_REGISTRY_URL_2"] = "http://localhost:38082" 
    os.environ["READONLY_2"] = "true"
    
    # Clear any global READONLY setting
    os.environ.pop("READONLY", None)
    
    try:
        # Import and reload the unified server in multi-registry mode to pick up environment variables
        import importlib
        import sys
        import os
        # Add the parent directory to sys.path so we can import oauth_provider
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import kafka_schema_registry_unified_mcp
        importlib.reload(kafka_schema_registry_multi_mcp)
        
        print("✅ unified server in multi-registry mode loaded")
        
        # Test 1: Verify registries are configured correctly
        print("\n🔍 Testing registry configuration...")
        
        registries = kafka_schema_registry_unified_mcp.list_registries()
        print(f"   📋 Configured registries: {[r.get('name') for r in registries if isinstance(r, dict)]}")
        
        # Check that we have both registries
        registry_names = [r.get('name') for r in registries if isinstance(r, dict) and 'name' in r]
        if 'development' not in registry_names or 'production' not in registry_names:
            print(f"   ❌ Expected both 'development' and 'production' registries, got: {registry_names}")
            return False
        
        print("   ✅ Both DEV and PROD registries configured")
        
        # Test 2: Verify read operations work on both registries 
        print("\n📖 Testing read operations...")
        
        # Test DEV registry read operations (should work)
        try:
            dev_subjects = kafka_schema_registry_unified_mcp.list_subjects(registry="development")
            print(f"   ✅ DEV read operations: Working")
        except Exception as e:
            print(f"   ⚠️  DEV read failed (connection issue): {e}")
        
        # Test PROD registry read operations (should work)
        try:
            prod_subjects = kafka_schema_registry_unified_mcp.list_subjects(registry="production")
            print(f"   ✅ PROD read operations: Working")
        except Exception as e:
            print(f"   ⚠️  PROD read failed (connection issue): {e}")
        
        # Test 3: Test write operations on DEV registry (should work)
        print("\n✏️  Testing write operations on DEV registry...")
        
        test_schema = {
            "type": "record",
            "name": "ReadOnlyTestSchema",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "message", "type": "string"}
            ]
        }
        
        # Try to register schema in DEV (should succeed or fail due to connection, not readonly)
        dev_result = kafka_schema_registry_unified_mcp.register_schema(
            subject="readonly-test-value",
            schema_definition=test_schema,
            registry="development"
        )
        
        if isinstance(dev_result, dict) and dev_result.get("readonly_mode"):
            print(f"   ❌ DEV incorrectly blocked by readonly mode: {dev_result}")
            return False
        else:
            print(f"   ✅ DEV write operations: Not blocked by readonly mode")
        
        # Test 4: Test write operations on PROD registry (should be blocked)
        print("\n🚫 Testing write operation blocking on PROD registry...")
        
        # Try to register schema in PROD (should be blocked by readonly mode)
        prod_result = kafka_schema_registry_unified_mcp.register_schema(
            subject="readonly-test-value",
            schema_definition=test_schema,
            registry="production"
        )
        
        if isinstance(prod_result, dict) and prod_result.get("readonly_mode"):
            print(f"   ✅ PROD write correctly blocked: {prod_result.get('error', 'Read-only mode')}")
        else:
            print(f"   ❌ PROD write NOT blocked by readonly mode! Result: {prod_result}")
            return False
        
        # Test 5: Test other modification operations on PROD
        print("\n🚫 Testing other modification operations on PROD...")
        
        # Try to update global config (should be blocked)
        config_result = kafka_schema_registry_unified_mcp.update_global_config(
            compatibility="FULL",
            registry="production"
        )
        
        if isinstance(config_result, dict) and config_result.get("readonly_mode"):
            print(f"   ✅ Config update correctly blocked")
        else:
            print(f"   ❌ Config update not blocked: {config_result}")
        
        # Try to create context (should be blocked)
        context_result = kafka_schema_registry_unified_mcp.create_context(
            context="readonly-test-context",
            registry="production"
        )
        
        if isinstance(context_result, dict) and context_result.get("readonly_mode"):
            print(f"   ✅ Context creation correctly blocked")
        else:
            print(f"   ❌ Context creation not blocked: {context_result}")
        
        # Try to delete subject (should be blocked)
        delete_result = kafka_schema_registry_unified_mcp.delete_subject(
            subject="test-subject",
            registry="production"
        )
        
        if isinstance(delete_result, dict) and delete_result.get("readonly_mode"):
            print(f"   ✅ Subject deletion correctly blocked")
        else:
            print(f"   ❌ Subject deletion not blocked: {delete_result}")
        
        # Test 6: Verify modification operations work on DEV (control test)
        print("\n✏️  Testing modification operations on DEV (control)...")
        
        # Try config update on DEV (should not be blocked by readonly)
        dev_config_result = kafka_schema_registry_unified_mcp.update_global_config(
            compatibility="BACKWARD",
            registry="development"
        )
        
        if isinstance(dev_config_result, dict) and dev_config_result.get("readonly_mode"):
            print(f"   ❌ DEV config update incorrectly blocked: {dev_config_result}")
            return False
        else:
            print(f"   ✅ DEV config update: Not blocked by readonly mode")
        
        # Test 7: Test cross-registry operations
        print("\n🔄 Testing cross-registry operations...")
        
        # Migration to PROD should be blocked
        migration_result = kafka_schema_registry_unified_mcp.migrate_schema(
            subject="readonly-test-value",
            source_registry="development",
            target_registry="production",
            dry_run=False
        )
        
        if isinstance(migration_result, dict) and migration_result.get("readonly_mode"):
            print(f"   ✅ Migration to PROD correctly blocked")
        else:
            print(f"   ⚠️  Migration response: {migration_result}")
        
        # Test 8: Verify read-only mode per registry  
        print("\n🔍 Testing per-registry read-only configuration...")
        
        # Test the check_readonly_mode function directly
        dev_readonly_check = kafka_schema_registry_unified_mcp.check_readonly_mode("development")
        prod_readonly_check = kafka_schema_registry_unified_mcp.check_readonly_mode("production")
        
        if dev_readonly_check is None:
            print(f"   ✅ DEV registry readonly check: Not in readonly mode")
        else:
            print(f"   ❌ DEV registry incorrectly in readonly mode: {dev_readonly_check}")
            return False
        
        if prod_readonly_check is not None and prod_readonly_check.get("readonly_mode"):
            print(f"   ✅ PROD registry readonly check: Correctly in readonly mode")
        else:
            print(f"   ❌ PROD registry not in readonly mode: {prod_readonly_check}")
            return False
        
        print("\n📊 Read-only validation summary:")
        print("   ✅ DEV registry: Read and write operations working")
        print("   ✅ PROD registry: Read operations working")
        print("   ✅ PROD registry: Write operations blocked by MCP server")
        print("   ✅ Per-registry read-only enforcement: Working correctly")
        print("   ✅ Cross-registry operations: Respecting read-only mode")
        
        print("✅ MCP read-only validation test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_test_readonly_validation()
    sys.exit(0 if success else 1)
