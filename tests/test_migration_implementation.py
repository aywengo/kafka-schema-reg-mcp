#!/usr/bin/env python3
"""
Test Migration Implementation Validation

This script validates that the newly implemented migration tests work correctly.
"""

import requests
import json
import sys
import subprocess
import os

def test_registry_connectivity():
    """Test that both registries are accessible"""
    print("🔍 Testing registry connectivity...")
    
    dev_url = "http://localhost:38081"
    prod_url = "http://localhost:38082"
    
    try:
        # Test DEV registry
        dev_response = requests.get(f"{dev_url}/subjects", timeout=5)
        if dev_response.status_code == 200:
            dev_subjects = len(dev_response.json())
            print(f"✅ DEV Registry (38081): {dev_subjects} subjects")
        else:
            print(f"❌ DEV Registry (38081): HTTP {dev_response.status_code}")
            return False
        
        # Test PROD registry
        prod_response = requests.get(f"{prod_url}/subjects", timeout=5)
        if prod_response.status_code == 200:
            prod_subjects = len(prod_response.json())
            print(f"✅ PROD Registry (38082): {prod_subjects} subjects")
        else:
            print(f"❌ PROD Registry (38082): HTTP {prod_response.status_code}")
            return False
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Registry connectivity failed: {e}")
        return False

def test_implemented_migration_files():
    """Test that all implemented migration test files exist and are valid"""
    print("\n🔍 Validating implemented migration test files...")
    
    implemented_files = [
        "test_schema_migration.py",
        "test_compatibility_migration.py", 
        "test_bulk_migration.py",
        "test_registry_comparison.py",
        "test_readonly_validation.py",
        "test_schema_drift.py",
        "test_version_migration.py"
    ]
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    valid_files = 0
    for test_file in implemented_files:
        file_path = os.path.join(script_dir, test_file)
        
        if os.path.exists(file_path):
            # Check if file has actual implementation (not skeleton)
            with open(file_path, 'r') as f:
                content = f.read()
                if "TODO: Implement actual test logic here" in content:
                    print(f"⚠️  {test_file}: Still a skeleton")
                else:
                    print(f"✅ {test_file}: Implemented")
                    valid_files += 1
        else:
            print(f"❌ {test_file}: Missing")
    
    print(f"\n📊 Implementation status: {valid_files}/{len(implemented_files)} files implemented")
    return valid_files == len(implemented_files)

def test_quick_migration_functionality():
    """Quick test of one migration function"""
    print("\n🧪 Quick migration functionality test...")
    
    dev_url = "http://localhost:38081"
    
    try:
        # Test creating a simple schema
        test_schema = {
            "type": "record",
            "name": "TestEvent",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "timestamp", "type": "long"}
            ]
        }
        
        payload = {"schema": json.dumps(test_schema)}
        
        response = requests.post(
            f"{dev_url}/subjects/migration-validation-test-value/versions",
            headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
            json=payload,
            timeout=5
        )
        
        if response.status_code in [200, 409]:  # 409 = already exists
            print("✅ Schema creation/validation successful")
            
            # Test retrieval
            get_response = requests.get(
                f"{dev_url}/subjects/migration-validation-test-value/versions/latest",
                timeout=5
            )
            
            if get_response.status_code == 200:
                schema_data = get_response.json()
                print(f"✅ Schema retrieval successful (version {schema_data.get('version')})")
                return True
            else:
                print(f"⚠️  Schema retrieval failed: {get_response.status_code}")
                return False
        else:
            print(f"⚠️  Schema creation failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Migration functionality test failed: {e}")
        return False

def run_sample_migration_test():
    """Run one of the implemented migration tests"""
    print("\n🚀 Running sample migration test (schema migration)...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_file = os.path.join(script_dir, "test_schema_migration.py")
    
    if os.path.exists(test_file):
        try:
            result = subprocess.run(
                [sys.executable, test_file],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("✅ Sample migration test passed!")
                print("   Last few lines of output:")
                output_lines = result.stdout.strip().split('\n')
                for line in output_lines[-3:]:
                    print(f"   {line}")
                return True
            else:
                print("❌ Sample migration test failed!")
                print("   Error output:")
                error_lines = result.stderr.strip().split('\n')
                for line in error_lines[-3:]:
                    print(f"   {line}")
                return False
                
        except subprocess.TimeoutExpired:
            print("⚠️  Sample migration test timed out")
            return False
        except Exception as e:
            print(f"❌ Failed to run sample test: {e}")
            return False
    else:
        print("❌ Sample test file not found")
        return False

def main():
    print("🧪 Migration Implementation Validation")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 4
    
    # Test 1: Registry connectivity
    if test_registry_connectivity():
        tests_passed += 1
    
    # Test 2: Implementation validation
    if test_implemented_migration_files():
        tests_passed += 1
    
    # Test 3: Quick functionality test
    if test_quick_migration_functionality():
        tests_passed += 1
    
    # Test 4: Sample migration test
    if run_sample_migration_test():
        tests_passed += 1
    
    print(f"\n📊 Validation Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("\n🎉 ALL MIGRATION IMPLEMENTATION VALIDATION PASSED!")
        print("✅ Ready to run full migration test suite:")
        print("   ./run_migration_tests.sh")
        return True
    else:
        print(f"\n⚠️  {total_tests - tests_passed} validation tests failed")
        print("❌ Check environment and implementation before running full suite")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 