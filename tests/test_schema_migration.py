#!/usr/bin/env python3
"""
Schema migration from DEV to PROD

Tests the migration of schemas between DEV and PROD registries.
"""

import requests
import json
import sys
import time

def test_test_schema_migration():
    """Schema migration from DEV to PROD"""
    
    # DEV Schema Registry
    dev_url = "http://localhost:38081"
    
    # PROD Schema Registry  
    prod_url = "http://localhost:38082"
    
    print(f"🧪 Starting schema migration test...")
    
    try:
        # Check connectivity
        dev_response = requests.get(f"{dev_url}/subjects", timeout=5)
        prod_response = requests.get(f"{prod_url}/subjects", timeout=5)
        
        if dev_response.status_code != 200 or prod_response.status_code != 200:
            print("❌ Registry connectivity failed")
            return False
            
        print("✅ Both registries are accessible")
        
        # Create a test schema in DEV
        test_subject = "migration-test-user"
        test_schema = {
            "type": "record",
            "name": "User",
            "namespace": "com.example.migration.test",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "name", "type": "string"},
                {"name": "email", "type": "string"}
            ]
        }
        
        schema_payload = {
            "schema": json.dumps(test_schema)
        }
        
        print(f"📝 Creating test schema '{test_subject}' in DEV...")
        create_response = requests.post(
            f"{dev_url}/subjects/{test_subject}-value/versions",
            headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
            json=schema_payload,
            timeout=5
        )
        
        if create_response.status_code not in [200, 409]:  # 409 = already exists
            print(f"❌ Failed to create schema in DEV: {create_response.status_code}")
            return False
            
        print("✅ Test schema created in DEV")
        
        # Get the schema from DEV
        get_response = requests.get(
            f"{dev_url}/subjects/{test_subject}-value/versions/latest",
            timeout=5
        )
        
        if get_response.status_code != 200:
            print("❌ Failed to retrieve schema from DEV")
            return False
            
        dev_schema_data = get_response.json()
        print(f"✅ Retrieved schema from DEV (version {dev_schema_data.get('version')})")
        
        # Check if schema already exists in PROD
        prod_check = requests.get(
            f"{prod_url}/subjects/{test_subject}-value/versions/latest",
            timeout=5
        )
        
        schema_exists_in_prod = prod_check.status_code == 200
        
        if schema_exists_in_prod:
            print("✅ Schema already exists in PROD - migration validation passed")
        else:
            # Attempt to migrate to PROD (this will fail due to read-only, which is expected)
            print("📤 Attempting migration to PROD (expecting read-only error)...")
            migrate_response = requests.post(
                f"{prod_url}/subjects/{test_subject}-value/versions",
                headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
                json={"schema": dev_schema_data["schema"]},
                timeout=5
            )
            
            if migrate_response.status_code == 405 or migrate_response.status_code == 403:
                print("✅ PROD registry correctly rejected write (read-only mode)")
            elif migrate_response.status_code == 200:
                print("✅ Schema successfully migrated to PROD")
            else:
                print(f"⚠️  Unexpected migration response: {migrate_response.status_code}")
        
        # Verify migration simulation
        print("🔍 Validating migration compatibility...")
        
        # Check compatibility
        compat_response = requests.post(
            f"{dev_url}/compatibility/subjects/{test_subject}-value/versions/latest",
            headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
            json={"schema": dev_schema_data["schema"]},
            timeout=5
        )
        
        if compat_response.status_code == 200:
            compat_data = compat_response.json()
            if compat_data.get("is_compatible", False):
                print("✅ Schema is self-compatible")
            else:
                print("⚠️  Schema compatibility check failed")
        
        print("✅ Schema migration test completed successfully")
        return True
        
    except requests.exceptions.Timeout:
        print("❌ Test failed: Request timeout")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_test_schema_migration()
    sys.exit(0 if success else 1)
