#!/usr/bin/env python3
"""
Simple test to verify integration test setup.
This script tests basic connectivity to Schema Registry and creates test data.
"""

import requests
import json
import time

# Configuration
SCHEMA_REGISTRY_URL = "http://localhost:38081"

def test_schema_registry_connection():
    """Test basic connection to Schema Registry."""
    print("🔧 Testing Schema Registry connection...")
    
    try:
        response = requests.get(f"{SCHEMA_REGISTRY_URL}/subjects", timeout=10)
        if response.status_code == 200:
            subjects = response.json()
            print(f"✅ Connected to Schema Registry: {len(subjects)} subjects found")
            return True
        else:
            print(f"❌ Schema Registry returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to Schema Registry: {e}")
        return False

def create_test_contexts():
    """Create test contexts for simulating multiple registries."""
    print("📁 Creating test contexts...")
    
    contexts = ["development", "staging", "production"]
    created_contexts = []
    
    for context in contexts:
        try:
            response = requests.post(f"{SCHEMA_REGISTRY_URL}/contexts/{context}")
            if response.status_code in [200, 409]:  # 409 = already exists
                print(f"✅ Context '{context}' ready")
                created_contexts.append(context)
            else:
                print(f"⚠️  Context '{context}' creation failed: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Error creating context '{context}': {e}")
    
    return created_contexts

def register_test_schemas():
    """Register test schemas in different contexts."""
    print("📋 Registering test schemas...")
    
    # Test schema
    user_schema = {
        "type": "record",
        "name": "User",
        "fields": [
            {"name": "id", "type": "long"},
            {"name": "name", "type": "string"},
            {"name": "email", "type": "string"}
        ]
    }
    
    contexts = ["development", "staging", "production"]
    subjects = ["user-events", "click-events"]
    
    registered_schemas = []
    
    for context in contexts:
        for subject in subjects:
            if context == "production" and subject == "click-events":
                # Skip some schemas in production to test differences
                continue
                
            try:
                url = f"{SCHEMA_REGISTRY_URL}/contexts/{context}/subjects/{subject}/versions"
                payload = {
                    "schema": json.dumps(user_schema),
                    "schemaType": "AVRO"
                }
                
                response = requests.post(
                    url,
                    data=json.dumps(payload),
                    headers={"Content-Type": "application/vnd.schemaregistry.v1+json"}
                )
                
                if response.status_code in [200, 409]:  # 409 = already exists
                    print(f"✅ Schema '{subject}' registered in '{context}'")
                    registered_schemas.append(f"{context}:{subject}")
                else:
                    print(f"⚠️  Failed to register '{subject}' in '{context}': {response.status_code}")
                    
            except Exception as e:
                print(f"⚠️  Error registering '{subject}' in '{context}': {e}")
    
    return registered_schemas

def list_schemas_by_context():
    """List schemas in each context to verify setup."""
    print("📋 Listing schemas by context...")
    
    contexts = ["development", "staging", "production"]
    
    for context in contexts:
        try:
            # List subjects in context
            response = requests.get(f"{SCHEMA_REGISTRY_URL}/contexts/{context}/subjects")
            if response.status_code == 200:
                subjects = response.json()
                print(f"✅ Context '{context}': {len(subjects)} subjects - {subjects}")
            else:
                print(f"⚠️  Context '{context}': Failed to list subjects ({response.status_code})")
        except Exception as e:
            print(f"⚠️  Error listing subjects in '{context}': {e}")

def test_numbered_config_locally():
    """Test the numbered configuration approach locally."""
    print("🔧 Testing numbered configuration approach...")
    
    import os
    import sys
    
    # Set up environment for multi-registry mode
    os.environ["SCHEMA_REGISTRY_NAME_1"] = "development"
    os.environ["SCHEMA_REGISTRY_URL_1"] = SCHEMA_REGISTRY_URL
    os.environ["READONLY_1"] = "false"
    
    os.environ["SCHEMA_REGISTRY_NAME_2"] = "staging"
    os.environ["SCHEMA_REGISTRY_URL_2"] = SCHEMA_REGISTRY_URL
    os.environ["READONLY_2"] = "false"
    
    os.environ["SCHEMA_REGISTRY_NAME_3"] = "production"
    os.environ["SCHEMA_REGISTRY_URL_3"] = SCHEMA_REGISTRY_URL
    os.environ["READONLY_3"] = "true"
    
    # Clear single registry config
    os.environ.pop("SCHEMA_REGISTRY_URL", None)
    
    try:
        # Add parent directory to Python path to find the main modules
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Import and test configuration loading
        import importlib
        if 'kafka_schema_registry_multi_mcp' in sys.modules:
            importlib.reload(sys.modules['kafka_schema_registry_multi_mcp'])
        else:
            import kafka_schema_registry_multi_mcp
        
        # Check registry manager
        registries = kafka_schema_registry_multi_mcp.registry_manager.list_registries()
        print(f"✅ Found {len(registries)} registries: {registries}")
        
        # Test per-registry readonly
        readonly_check = kafka_schema_registry_multi_mcp.check_readonly_mode("production")
        if readonly_check:
            print("✅ Per-registry READONLY working for production")
        else:
            print("❌ Per-registry READONLY not working for production")
            
        readonly_check_dev = kafka_schema_registry_multi_mcp.check_readonly_mode("development")
        if readonly_check_dev:
            print("❌ Development should not be readonly")
        else:
            print("✅ Development is not readonly (correct)")
            
        return True
        
    except Exception as e:
        print(f"❌ Numbered configuration test failed: {e}")
        return False

def main():
    """Run all setup tests."""
    print("🧪 Integration Setup Test")
    print("=" * 40)
    
    success = True
    
    # Test 1: Basic connection
    if not test_schema_registry_connection():
        print("\n❌ Basic connection test failed!")
        print("💡 Make sure docker-compose services are running:")
        print("   docker-compose up -d")
        return False
    
    # Test 2: Create contexts
    print()
    contexts = create_test_contexts()
    if len(contexts) < 3:
        print("⚠️  Not all contexts were created successfully")
        success = False
    
    # Test 3: Register schemas
    print()
    schemas = register_test_schemas()
    if len(schemas) < 5:  # Expecting at least 5 schemas
        print("⚠️  Not all test schemas were registered")
        success = False
    
    # Test 4: List schemas
    print()
    list_schemas_by_context()
    
    # Test 5: Test numbered configuration
    print()
    if not test_numbered_config_locally():
        success = False
    
    # Summary
    print("\n" + "=" * 40)
    if success:
        print("✅ Integration setup test completed successfully!")
        print("\n📋 Setup Summary:")
        print("   ✅ Schema Registry connection working")
        print("   ✅ Test contexts created")
        print("   ✅ Test schemas registered")
        print("   ✅ Numbered configuration working")
        print("\n🚀 Ready to run full integration tests!")
        print("   Run: ./run_numbered_integration_tests.sh")
    else:
        print("❌ Integration setup test failed!")
        print("\n🔍 Troubleshooting:")
        print("   1. Ensure docker-compose services are running: docker-compose up -d")
        print("   2. Wait for services to be fully ready (may take 1-2 minutes)")
        print("   3. Check Schema Registry at http://localhost:38081/subjects")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 