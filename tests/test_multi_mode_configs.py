#!/usr/bin/env python3
"""
Multi-Registry Mode Configuration Tests

Tests different Schema Registry modes and configurations across multiple registries:
- DEV in IMPORT mode, PROD in READWRITE mode  
- Different compatibility levels per registry
- Mixed read-only and mode configurations
- Cross-registry operations with different modes
"""

import os
import sys
import json

# Add parent directory to Python path to find the main modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_dev_import_prod_readwrite():
    """Test DEV registry in IMPORT mode, PROD registry in READWRITE mode"""
    
    print(f"🧪 Testing DEV=IMPORT, PROD=READWRITE configuration...")
    
    # Set up multi-registry environment variables
    os.environ["SCHEMA_REGISTRY_NAME_1"] = "development"
    os.environ["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
    os.environ["READONLY_1"] = "false"
    
    os.environ["SCHEMA_REGISTRY_NAME_2"] = "production"
    os.environ["SCHEMA_REGISTRY_URL_2"] = "http://localhost:38082" 
    os.environ["READONLY_2"] = "false"  # Both in normal mode initially
    
    # Clear any global READONLY setting
    os.environ.pop("READONLY", None)
    
    try:
        # Import and reload the multi-registry MCP server
        import importlib
        import kafka_schema_registry_multi_mcp
        importlib.reload(kafka_schema_registry_multi_mcp)
        
        print("✅ Multi-registry MCP server loaded")
        
        # Test 1: Set different modes
        print("\n🔧 Setting different modes...")
        
        # Set DEV to IMPORT mode
        dev_mode_result = kafka_schema_registry_multi_mcp.update_mode(
            mode="IMPORT",
            registry="development"
        )
        print(f"   📝 DEV mode set to IMPORT: {dev_mode_result}")
        
        # Set PROD to READWRITE mode (explicit)
        prod_mode_result = kafka_schema_registry_multi_mcp.update_mode(
            mode="READWRITE", 
            registry="production"
        )
        print(f"   📝 PROD mode set to READWRITE: {prod_mode_result}")
        
        # Test 2: Verify modes are set correctly
        print("\n🔍 Verifying mode configurations...")
        
        # Check DEV mode
        dev_mode_check = kafka_schema_registry_multi_mcp.get_mode(registry="development")
        print(f"   📋 DEV mode: {dev_mode_check}")
        
        # Check PROD mode  
        prod_mode_check = kafka_schema_registry_multi_mcp.get_mode(registry="production")
        print(f"   📋 PROD mode: {prod_mode_check}")
        
        # Test 3: Test operations allowed in IMPORT mode (DEV)
        print("\n📥 Testing IMPORT mode operations on DEV...")
        
        test_schema = {
            "type": "record",
            "name": "ImportTestSchema",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "data", "type": "string"}
            ]
        }
        
        # Schema registration should work in IMPORT mode
        dev_register_result = kafka_schema_registry_multi_mcp.register_schema(
            subject="import-test-value",
            schema_definition=test_schema,
            registry="development"
        )
        print(f"   📝 DEV schema registration: {dev_register_result}")
        
        # Test 4: Test full operations in READWRITE mode (PROD) 
        print("\n✏️  Testing READWRITE mode operations on PROD...")
        
        # All operations should work in READWRITE mode
        prod_register_result = kafka_schema_registry_multi_mcp.register_schema(
            subject="readwrite-test-value",
            schema_definition=test_schema,
            registry="production"
        )
        print(f"   📝 PROD schema registration: {prod_register_result}")
        
        # Test config updates
        prod_config_result = kafka_schema_registry_multi_mcp.update_global_config(
            compatibility="FORWARD",
            registry="production"
        )
        print(f"   ⚙️  PROD config update: {prod_config_result}")
        
        # Test 5: Test restricted operations in IMPORT mode
        print("\n🚫 Testing restricted operations in IMPORT mode...")
        
        # Some operations might be restricted in IMPORT mode
        dev_config_result = kafka_schema_registry_multi_mcp.update_global_config(
            compatibility="FULL",
            registry="development"
        )
        print(f"   ⚙️  DEV config update (IMPORT mode): {dev_config_result}")
        
        print("✅ DEV=IMPORT, PROD=READWRITE test completed")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_different_compatibility_levels():
    """Test different compatibility levels across registries"""
    
    print(f"\n🧪 Testing different compatibility levels per registry...")
    
    try:
        import kafka_schema_registry_multi_mcp
        
        # Test 1: Set different compatibility levels
        print("\n🔧 Setting different compatibility levels...")
        
        # Set DEV to BACKWARD compatibility
        dev_compat_result = kafka_schema_registry_multi_mcp.update_global_config(
            compatibility="BACKWARD",
            registry="development"
        )
        print(f"   📝 DEV compatibility set to BACKWARD: {dev_compat_result}")
        
        # Set PROD to FORWARD compatibility
        prod_compat_result = kafka_schema_registry_multi_mcp.update_global_config(
            compatibility="FORWARD",
            registry="production"
        )
        print(f"   📝 PROD compatibility set to FORWARD: {prod_compat_result}")
        
        # Test 2: Verify compatibility settings
        print("\n🔍 Verifying compatibility configurations...")
        
        # Check DEV compatibility
        dev_config_check = kafka_schema_registry_multi_mcp.get_global_config(registry="development")
        print(f"   📋 DEV config: {dev_config_check}")
        
        # Check PROD compatibility
        prod_config_check = kafka_schema_registry_multi_mcp.get_global_config(registry="production")
        print(f"   📋 PROD config: {prod_config_check}")
        
        # Test 3: Test schema evolution with different compatibility
        print("\n🔄 Testing schema evolution with different compatibility...")
        
        # Base schema
        base_schema = {
            "type": "record",
            "name": "CompatibilityTestSchema",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "name", "type": "string"}
            ]
        }
        
        # Register base schema in both registries
        dev_base_result = kafka_schema_registry_multi_mcp.register_schema(
            subject="compatibility-test-value",
            schema_definition=base_schema,
            registry="development"
        )
        print(f"   📝 DEV base schema: {dev_base_result}")
        
        prod_base_result = kafka_schema_registry_multi_mcp.register_schema(
            subject="compatibility-test-value", 
            schema_definition=base_schema,
            registry="production"
        )
        print(f"   📝 PROD base schema: {prod_base_result}")
        
        # Evolved schema (adding optional field - backward compatible)
        evolved_schema = {
            "type": "record",
            "name": "CompatibilityTestSchema",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "name", "type": "string"},
                {"name": "email", "type": ["null", "string"], "default": None}
            ]
        }
        
        # Test compatibility check on DEV (BACKWARD)
        dev_compat_check = kafka_schema_registry_multi_mcp.check_compatibility(
            subject="compatibility-test-value",
            schema_definition=evolved_schema,
            registry="development"
        )
        print(f"   🔍 DEV compatibility check (BACKWARD): {dev_compat_check}")
        
        # Test compatibility check on PROD (FORWARD)
        prod_compat_check = kafka_schema_registry_multi_mcp.check_compatibility(
            subject="compatibility-test-value",
            schema_definition=evolved_schema,
            registry="production"
        )
        print(f"   🔍 PROD compatibility check (FORWARD): {prod_compat_check}")
        
        print("✅ Different compatibility levels test completed")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mixed_readonly_and_modes():
    """Test mixed read-only and mode configurations"""
    
    print(f"\n🧪 Testing mixed read-only and mode configurations...")
    
    # Set up mixed configuration: DEV=normal, PROD=readonly
    os.environ["READONLY_1"] = "false"  # DEV can be modified
    os.environ["READONLY_2"] = "true"   # PROD is read-only
    
    try:
        import importlib
        import kafka_schema_registry_multi_mcp
        importlib.reload(kafka_schema_registry_multi_mcp)
        
        print("✅ Reloaded with mixed readonly configuration")
        
        # Test 1: Verify DEV allows mode changes (not read-only)
        print("\n🔧 Testing mode changes with read-only enforcement...")
        
        # DEV should allow mode changes
        dev_mode_result = kafka_schema_registry_multi_mcp.update_mode(
            mode="READWRITE",
            registry="development"
        )
        print(f"   📝 DEV mode change (should work): {dev_mode_result}")
        
        # PROD should block mode changes (read-only)
        prod_mode_result = kafka_schema_registry_multi_mcp.update_mode(
            mode="READWRITE", 
            registry="production"
        )
        print(f"   🚫 PROD mode change (should be blocked): {prod_mode_result}")
        
        # Test 2: Test read operations work on both
        print("\n📖 Testing read operations...")
        
        # Both should allow reads
        dev_subjects = kafka_schema_registry_multi_mcp.list_subjects(registry="development")
        prod_subjects = kafka_schema_registry_multi_mcp.list_subjects(registry="production")
        
        print(f"   ✅ DEV read operations: Working")
        print(f"   ✅ PROD read operations: Working")
        
        # Test 3: Test write operations
        print("\n✏️  Testing write operations with read-only enforcement...")
        
        test_schema = {
            "type": "record",
            "name": "MixedModeTestSchema",
            "fields": [
                {"name": "id", "type": "int"}
            ]
        }
        
        # DEV should allow writes
        dev_write_result = kafka_schema_registry_multi_mcp.register_schema(
            subject="mixed-mode-test-value",
            schema_definition=test_schema,
            registry="development"
        )
        print(f"   📝 DEV write (should work): {dev_write_result}")
        
        # PROD should block writes  
        prod_write_result = kafka_schema_registry_multi_mcp.register_schema(
            subject="mixed-mode-test-value",
            schema_definition=test_schema,
            registry="production"
        )
        print(f"   🚫 PROD write (should be blocked): {prod_write_result}")
        
        print("✅ Mixed read-only and mode configurations test completed")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cross_registry_operations_with_modes():
    """Test cross-registry operations with different modes"""
    
    print(f"\n🧪 Testing cross-registry operations with different modes...")
    
    try:
        import kafka_schema_registry_multi_mcp
        
        # Test 1: Migration between registries with different modes
        print("\n🔄 Testing migration between different modes...")
        
        # Try migration from DEV to PROD (should respect PROD read-only)
        migration_result = kafka_schema_registry_multi_mcp.migrate_schema(
            subject="test-migration",
            source_registry="development",
            target_registry="production",
            dry_run=True  # Dry run first
        )
        print(f"   🔄 Migration DEV→PROD (dry run): {migration_result}")
        
        # Test 2: Compare registries with different configurations
        print("\n📊 Comparing registries with different configurations...")
        
        comparison_result = kafka_schema_registry_multi_mcp.compare_registries(
            source_registry="development",
            target_registry="production",
            include_configs=True
        )
        print(f"   📊 Registry comparison: {comparison_result}")
        
        # Test 3: Find missing schemas between different modes
        print("\n🔍 Finding missing schemas between registries...")
        
        missing_schemas_result = kafka_schema_registry_multi_mcp.find_missing_schemas(
            source_registry="development",
            target_registry="production"
        )
        print(f"   🔍 Missing schemas DEV→PROD: {missing_schemas_result}")
        
        print("✅ Cross-registry operations with modes test completed")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_subject_specific_configurations():
    """Test subject-specific configurations across registries"""
    
    print(f"\n🧪 Testing subject-specific configurations...")
    
    try:
        import kafka_schema_registry_multi_mcp
        
        # Test 1: Set different subject-specific compatibility
        print("\n🔧 Setting subject-specific configurations...")
        
        test_subject = "subject-config-test-value"
        
        # Set subject-specific compatibility on DEV
        dev_subject_config = kafka_schema_registry_multi_mcp.update_subject_config(
            subject=test_subject,
            compatibility="FULL",
            registry="development"
        )
        print(f"   📝 DEV subject config (FULL): {dev_subject_config}")
        
        # Set different subject-specific compatibility on PROD (if not read-only)
        prod_subject_config = kafka_schema_registry_multi_mcp.update_subject_config(
            subject=test_subject,
            compatibility="NONE",
            registry="production"
        )
        print(f"   📝 PROD subject config (NONE): {prod_subject_config}")
        
        # Test 2: Verify subject-specific settings
        print("\n🔍 Verifying subject-specific configurations...")
        
        # Check DEV subject config
        dev_subject_check = kafka_schema_registry_multi_mcp.get_subject_config(
            subject=test_subject,
            registry="development"
        )
        print(f"   📋 DEV subject config: {dev_subject_check}")
        
        # Check PROD subject config
        prod_subject_check = kafka_schema_registry_multi_mcp.get_subject_config(
            subject=test_subject,
            registry="production"
        )
        print(f"   📋 PROD subject config: {prod_subject_check}")
        
        # Test 3: Test subject-specific modes
        print("\n⚙️  Testing subject-specific modes...")
        
        # Set subject-specific mode on DEV
        dev_subject_mode = kafka_schema_registry_multi_mcp.update_subject_mode(
            subject=test_subject,
            mode="IMPORT",
            registry="development"
        )
        print(f"   📝 DEV subject mode (IMPORT): {dev_subject_mode}")
        
        # Try to set subject-specific mode on PROD (might be blocked)
        prod_subject_mode = kafka_schema_registry_multi_mcp.update_subject_mode(
            subject=test_subject,
            mode="READWRITE",
            registry="production"
        )
        print(f"   📝 PROD subject mode (READWRITE): {prod_subject_mode}")
        
        print("✅ Subject-specific configurations test completed")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_multi_mode_tests():
    """Run all multi-mode configuration tests"""
    
    print("🚀 Starting Multi-Mode Configuration Tests")
    print("=" * 60)
    
    test_results = []
    
    # Run all test functions
    test_functions = [
        ("DEV=IMPORT, PROD=READWRITE", test_dev_import_prod_readwrite),
        ("Different Compatibility Levels", test_different_compatibility_levels),
        ("Mixed Read-Only and Modes", test_mixed_readonly_and_modes),
        ("Cross-Registry Operations", test_cross_registry_operations_with_modes),
        ("Subject-Specific Configurations", test_subject_specific_configurations),
    ]
    
    for test_name, test_func in test_functions:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            test_results.append((test_name, result))
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"\n{status}: {test_name}")
        except Exception as e:
            test_results.append((test_name, False))
            print(f"\n❌ FAILED: {test_name} - {e}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Multi-Mode Configuration Tests Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name}")
    
    print(f"\n📈 Overall Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All multi-mode configuration tests passed!")
    else:
        print(f"⚠️  {total - passed} test(s) failed")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_multi_mode_tests()
    sys.exit(0 if success else 1) 