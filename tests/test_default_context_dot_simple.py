#!/usr/bin/env python3
"""
Simplified Default Context "." Test - Read-Only Compatible

This test works with read-only Schema Registries by testing
default context functionality without creating new schemas.
"""

import os
import sys

# Add parent directory to path to import the MCP server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_default_context_url_building():
    """Test that URL building correctly handles default context '.'"""
    print("🧪 Testing URL building for default context '.'...")
    
    try:
        import kafka_schema_registry_multi_mcp as mcp_server
        
        # Setup minimal environment
        os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
        os.environ["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
        
        # Reinitialize registry manager
        mcp_server.registry_manager._load_registries()
        
        # Get client
        client = mcp_server.registry_manager.get_registry("dev")
        if not client:
            print("   ❌ Could not get dev registry client")
            return False
        
        # Test URL building with different context values
        url_none = client.build_context_url("/subjects", None)
        url_dot = client.build_context_url("/subjects", ".")
        url_named = client.build_context_url("/subjects", "production")
        
        print(f"   🔗 URL with context=None: {url_none}")
        print(f"   🔗 URL with context='.': {url_dot}")
        print(f"   🔗 URL with context='production': {url_named}")
        
        # Key test: context="." should produce the same URL as context=None
        if url_dot != url_none:
            print(f"   ❌ CRITICAL: URL for context='.' differs from context=None")
            return False
        
        # Named context should be different
        if url_named == url_none:
            print(f"   ❌ Named context URL should be different from default")
            return False
        
        print(f"   ✅ URL building test PASSED")
        return True
        
    except Exception as e:
        print(f"   ❌ URL building test failed: {e}")
        return False

def test_default_context_subject_listing():
    """Test that subject listing works for default context '.' (read-only compatible)"""
    print("\n🧪 Testing subject listing for default context '.' (read-only mode)...")
    
    try:
        import kafka_schema_registry_multi_mcp as mcp_server
        
        # Test listing subjects with different context parameters
        subjects_none = mcp_server.list_subjects(context=None, registry="dev")
        subjects_dot = mcp_server.list_subjects(context=".", registry="dev")
        
        print(f"   📋 Found {len(subjects_none)} subjects with context=None")
        print(f"   📋 Found {len(subjects_dot)} subjects with context='.'")
        
        # Both should return the same results
        if len(subjects_none) != len(subjects_dot):
            print(f"   ❌ CRITICAL: Different results for context=None vs context='.'!")
            print(f"      context=None: {len(subjects_none)} subjects")
            print(f"      context='.': {len(subjects_dot)} subjects")
            return False
        
        # Check that the actual subjects are the same
        if set(subjects_none) != set(subjects_dot):
            print(f"   ❌ CRITICAL: Different subjects returned for context=None vs context='.'!")
            diff_none_only = set(subjects_none) - set(subjects_dot)
            diff_dot_only = set(subjects_dot) - set(subjects_none)
            if diff_none_only:
                print(f"      Only in context=None: {list(diff_none_only)[:3]}...")
            if diff_dot_only:
                print(f"      Only in context='.': {list(diff_dot_only)[:3]}...")
            return False
        
        print(f"   ✅ Subject listing test PASSED")
        print(f"   ℹ️  Both context=None and context='.' return identical results")
        return True
        
    except Exception as e:
        print(f"   ❌ Subject listing test failed: {e}")
        return False

def test_schema_registry_connectivity():
    """Test basic Schema Registry connectivity and read-only status"""
    print("\n🧪 Testing Schema Registry connectivity and status...")
    
    try:
        import requests
        
        # Test basic connectivity
        response = requests.get("http://localhost:38081/subjects", timeout=5)
        if response.status_code == 200:
            subjects = response.json()
            print(f"   ✅ Schema Registry is accessible")
            print(f"   📋 Found {len(subjects)} total subjects")
            
            # Test if it's read-only by attempting a simple operation
            try:
                # Try to get mode (this should work in read-only)
                mode_response = requests.get("http://localhost:38081/mode", timeout=5)
                if mode_response.status_code == 200:
                    mode_data = mode_response.json()
                    mode = mode_data.get("mode", "unknown")
                    print(f"   📊 Schema Registry mode: {mode}")
                    
                    if mode == "READONLY":
                        print(f"   ℹ️  Registry is in READONLY mode (expected)")
                    else:
                        print(f"   ℹ️  Registry mode: {mode}")
                        
            except Exception:
                print(f"   ℹ️  Could not determine registry mode")
            
            return True
        else:
            print(f"   ❌ Schema Registry returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Schema Registry connectivity test failed: {e}")
        return False

async def main():
    """Run simplified default context tests (read-only compatible)"""
    print("🚀 Starting Read-Only Compatible Default Context '.' Tests")
    print("=" * 60)
    print("ℹ️  This test works with read-only Schema Registries")
    print("ℹ️  No schema creation required - tests existing functionality")
    print("=" * 60)
    
    tests = [
        ("Schema Registry Connectivity", test_schema_registry_connectivity),
        ("URL Building", test_default_context_url_building),
        ("Subject Listing", test_default_context_subject_listing)
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
        print(f"\n🎉 ALL READ-ONLY COMPATIBLE TESTS PASSED!")
        print(f"✅ Default context '.' functionality works correctly")
        print(f"✅ URL building handles context='.' properly") 
        print(f"✅ Subject listing works for default context")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed")
        return False

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 