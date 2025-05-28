#!/usr/bin/env python3
"""
Quick Schema Registry connectivity and error diagnosis
"""

import requests
import json

def quick_check():
    """Quick check of Schema Registry status"""
    print("🔍 Quick Schema Registry Check")
    print("=" * 40)
    
    # Test DEV registry
    try:
        print("\n📡 Testing DEV Registry (38081)...")
        dev_response = requests.get("http://localhost:38081/subjects", timeout=5)
        print(f"   Status: {dev_response.status_code}")
        if dev_response.status_code == 200:
            subjects = dev_response.json()
            print(f"   Subjects: {len(subjects)} found")
        else:
            print(f"   Error: {dev_response.text}")
    except Exception as e:
        print(f"   ❌ DEV registry not accessible: {e}")
        return False
    
    # Test PROD registry
    try:
        print("\n📡 Testing PROD Registry (38082)...")
        prod_response = requests.get("http://localhost:38082/subjects", timeout=5)
        print(f"   Status: {prod_response.status_code}")
        if prod_response.status_code == 200:
            subjects = prod_response.json()
            print(f"   Subjects: {len(subjects)} found")
        else:
            print(f"   Error: {prod_response.text}")
    except Exception as e:
        print(f"   ❌ PROD registry not accessible: {e}")
        return False
    
    # Test schema registration in DEV
    print("\n🧪 Testing Schema Registration in DEV...")
    test_schema = {
        "type": "record",
        "name": "QuickTest",
        "namespace": "com.example.test",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "name", "type": "string"}
        ]
    }
    
    payload = {"schema": json.dumps(test_schema)}
    
    try:
        reg_response = requests.post(
            "http://localhost:38081/subjects/quick-test-subject-value/versions",
            headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
            json=payload,
            timeout=10
        )
        
        print(f"   Registration Status: {reg_response.status_code}")
        
        if reg_response.status_code == 200:
            print("   ✅ Schema registration successful!")
            result = reg_response.json()
            print(f"   Schema ID: {result.get('id')}")
        elif reg_response.status_code == 409:
            print("   ✅ Schema already exists (409)")
        elif reg_response.status_code == 422:
            print("   ❌ Schema validation failed (422)")
            try:
                error_details = reg_response.json()
                print(f"   Error details: {error_details}")
            except:
                print(f"   Raw error: {reg_response.text}")
        else:
            print(f"   ❌ Unexpected error: {reg_response.status_code}")
            print(f"   Response: {reg_response.text}")
            
    except Exception as e:
        print(f"   ❌ Registration test failed: {e}")
    
    print("\n💡 Troubleshooting:")
    print("   1. Check if multi-registry environment is running:")
    print("      ./tests/start_multi_registry_environment.sh")
    print("   2. Check Docker containers:")
    print("      docker ps | grep schema-registry")
    print("   3. Check logs:")
    print("      docker logs kafka-schema-reg-mcp-dev-schema-registry-1")
    
    return True

if __name__ == "__main__":
    quick_check() 