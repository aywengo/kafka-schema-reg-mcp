#!/usr/bin/env python3
"""
Single-Registry Test Runner Validation

This script validates that the single-registry test runner components
are compatible and can be imported successfully.
"""

import os
import sys

# Add project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def validate_single_registry_tests():
    """Validate that single-registry test components are available and compatible"""
    print("🔍 Validating Single-Registry Test Runner Components")
    print("=" * 60)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Single-registry test files that should work
    working_tests = [
        "test_basic_server.py",
        "test_mcp_server.py",
        "test_config.py", 
        "test_readonly_mcp_client.py",
        "test_integration.py",
        "advanced_mcp_test.py",
        "test_docker_mcp.py",
        "test_simple_python.py"
    ]
    
    # Tests that are incompatible/skipped
    incompatible_tests = [
        "test_unit.py",  # FastAPI-based, incompatible with MCP
    ]
    
    # Multi-registry tests that should be excluded
    excluded_tests = [
        "test_numbered_config.py",
        "test_default_context_dot_migration.py",
        "test_end_to_end_workflows.py",
        "test_error_handling.py",
        "test_performance_load.py"
    ]
    
    found_working = []
    missing_working = []
    found_incompatible = []
    found_excluded = []
    
    print("📋 Checking Compatible Single-Registry Tests:")
    for test_file in working_tests:
        test_path = os.path.join(script_dir, test_file)
        if os.path.exists(test_path):
            print(f"   ✅ {test_file}")
            found_working.append(test_file)
        else:
            print(f"   ❌ {test_file} (MISSING)")
            missing_working.append(test_file)
    
    print(f"\n📋 Checking Incompatible Tests (should be skipped):")
    for test_file in incompatible_tests:
        test_path = os.path.join(script_dir, test_file)
        if os.path.exists(test_path):
            print(f"   ⚠️  {test_file} (exists but incompatible)")
            found_incompatible.append(test_file)
        else:
            print(f"   ✅ {test_file} (not found, which is fine)")
    
    print(f"\n📋 Checking Multi-Registry Tests (should be excluded):")
    for test_file in excluded_tests:
        test_path = os.path.join(script_dir, test_file)
        if os.path.exists(test_path):
            print(f"   ⚠️  {test_file} (exists but excluded from single-registry)")
            found_excluded.append(test_file)
        else:
            print(f"   ✅ {test_file} (not found, which is fine)")
    
    # Test basic imports
    print(f"\n🧪 Testing Basic Imports:")
    try:
        import kafka_schema_registry_mcp
        print(f"   ✅ kafka_schema_registry_mcp can be imported")
    except ImportError as e:
        print(f"   ❌ Cannot import kafka_schema_registry_mcp: {e}")
        return False
    
    try:
        from mcp import ClientSession, StdioServerParameters
        print(f"   ✅ MCP components can be imported")
    except ImportError as e:
        print(f"   ❌ Cannot import MCP components: {e}")
        return False
    
    try:
        import requests
        print(f"   ✅ Requests can be imported")
    except ImportError as e:
        print(f"   ❌ Cannot import requests: {e}")
        return False
    
    # Summary
    print(f"\n📊 Validation Summary:")
    print(f"   Compatible Tests: {len(found_working)}/{len(working_tests)} found")
    print(f"   Incompatible Tests: {len(found_incompatible)} found (will be skipped)")
    print(f"   Multi-Registry Tests: {len(found_excluded)} found (will be excluded)")
    
    if missing_working:
        print(f"\n❌ VALIDATION FAILED")
        print(f"   Missing required single-registry tests:")
        for test in missing_working:
            print(f"     • {test}")
        return False
    else:
        print(f"\n✅ VALIDATION PASSED")
        print(f"   All required single-registry components are available!")
        print(f"   The single-registry test runner is ready to use.")
        
        if found_incompatible:
            print(f"\n⚠️  Incompatible tests found (will be automatically skipped):")
            for test in found_incompatible:
                print(f"     • {test} (FastAPI-based, incompatible with MCP)")
        
        if found_excluded:
            print(f"\n⚠️  Multi-registry tests found (excluded from single-registry runner):")
            for test in found_excluded[:3]:  # Show first 3
                print(f"     • {test}")
            if len(found_excluded) > 3:
                print(f"     ... and {len(found_excluded) - 3} more")
        
        print(f"\n🚀 Usage:")
        print(f"   ./run_comprehensive_tests.sh           # Run all compatible tests")
        print(f"   ./run_comprehensive_tests.sh --basic   # Run only basic tests")
        print(f"   ./run_comprehensive_tests.sh --help    # Show all options")
        
        return True

if __name__ == "__main__":
    success = validate_single_registry_tests()
    sys.exit(0 if success else 1) 