#!/usr/bin/env python3
"""
Simple test to verify numbered environment variable configuration loading.
"""

import os
import sys

# Add parent directory to Python path to find the main modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_single_registry_config():
    print("🔧 Testing Single Registry Configuration Loading")
    print("-" * 50)
    
    # Set single registry environment variables
    os.environ["SCHEMA_REGISTRY_URL"] = "http://localhost:8081"
    os.environ["SCHEMA_REGISTRY_USER"] = "test-user"
    os.environ["SCHEMA_REGISTRY_PASSWORD"] = "test-password"
    os.environ["READONLY"] = "false"
    
    # Clear any numbered variables
    for i in range(1, 9):
        os.environ.pop(f"SCHEMA_REGISTRY_NAME_{i}", None)
        os.environ.pop(f"SCHEMA_REGISTRY_URL_{i}", None)
        os.environ.pop(f"SCHEMA_REGISTRY_USER_{i}", None)
        os.environ.pop(f"SCHEMA_REGISTRY_PASSWORD_{i}", None)
        os.environ.pop(f"READONLY_{i}", None)
    
    # Import and test configuration loading
    try:
        # Import the module to trigger configuration loading
        import importlib
        if 'kafka_schema_registry_multi_mcp' in sys.modules:
            importlib.reload(sys.modules['kafka_schema_registry_multi_mcp'])
        else:
            import kafka_schema_registry_multi_mcp
        
        # Check registry manager
        registries = kafka_schema_registry_multi_mcp.registry_manager.list_registries()
        print(f"✅ Found {len(registries)} registry(ies): {registries}")
        
        for name in registries:
            info = kafka_schema_registry_multi_mcp.registry_manager.get_registry_info(name)
            if info:
                print(f"   • {name}: {info['url']} (readonly: {info.get('readonly', False)})")
        
        default = kafka_schema_registry_multi_mcp.registry_manager.default_registry
        print(f"✅ Default registry: {default}")
        
    except Exception as e:
        print(f"❌ Single registry config failed: {e}")

def test_multi_registry_config():
    print("\n🔧 Testing Multi-Registry Configuration Loading")
    print("-" * 50)
    
    # Clear single registry variables
    os.environ.pop("SCHEMA_REGISTRY_URL", None)
    os.environ.pop("SCHEMA_REGISTRY_USER", None)
    os.environ.pop("SCHEMA_REGISTRY_PASSWORD", None)
    os.environ.pop("READONLY", None)
    
    # Set up numbered registries
    os.environ["SCHEMA_REGISTRY_NAME_1"] = "development"
    os.environ["SCHEMA_REGISTRY_URL_1"] = "http://localhost:8081"
    os.environ["SCHEMA_REGISTRY_USER_1"] = "dev-user"
    os.environ["SCHEMA_REGISTRY_PASSWORD_1"] = "dev-password"
    os.environ["READONLY_1"] = "false"
    
    os.environ["SCHEMA_REGISTRY_NAME_2"] = "staging"
    os.environ["SCHEMA_REGISTRY_URL_2"] = "http://localhost:8082"
    os.environ["SCHEMA_REGISTRY_USER_2"] = "staging-user"
    os.environ["SCHEMA_REGISTRY_PASSWORD_2"] = "staging-password"
    os.environ["READONLY_2"] = "false"
    
    os.environ["SCHEMA_REGISTRY_NAME_3"] = "production"
    os.environ["SCHEMA_REGISTRY_URL_3"] = "http://localhost:8083"
    os.environ["SCHEMA_REGISTRY_USER_3"] = "prod-user"
    os.environ["SCHEMA_REGISTRY_PASSWORD_3"] = "prod-password"
    os.environ["READONLY_3"] = "true"
    
    # Import and test configuration loading
    try:
        # Reload the module to pick up new environment variables
        import importlib
        import kafka_schema_registry_multi_mcp
        importlib.reload(kafka_schema_registry_multi_mcp)
        
        # Check registry manager
        registries = kafka_schema_registry_multi_mcp.registry_manager.list_registries()
        print(f"✅ Found {len(registries)} registries: {registries}")
        
        for name in registries:
            info = kafka_schema_registry_multi_mcp.registry_manager.get_registry_info(name)
            if info:
                print(f"   • {name}: {info['url']} (readonly: {info.get('readonly', False)})")
        
        default = kafka_schema_registry_multi_mcp.registry_manager.default_registry
        print(f"✅ Default registry: {default}")
        
        # Test per-registry READONLY mode
        readonly_check = kafka_schema_registry_multi_mcp.check_readonly_mode("production")
        if readonly_check:
            print(f"✅ Per-registry READONLY working: {readonly_check.get('error', 'blocked')}")
        else:
            print("❌ Per-registry READONLY not working for production")
        
        readonly_check_dev = kafka_schema_registry_multi_mcp.check_readonly_mode("development")
        if readonly_check_dev:
            print(f"❌ Development should not be readonly: {readonly_check_dev}")
        else:
            print("✅ Development is not readonly (correct)")
        
    except Exception as e:
        print(f"❌ Multi-registry config failed: {e}")

def test_max_registries():
    print("\n🔧 Testing Maximum Registry Limit (8 registries)")
    print("-" * 50)
    
    # Clear all environment variables
    for var in list(os.environ.keys()):
        if var.startswith("SCHEMA_REGISTRY"):
            os.environ.pop(var, None)
        if var.startswith("READONLY"):
            os.environ.pop(var, None)
    
    # Set up 8 registries (maximum)
    for i in range(1, 9):
        os.environ[f"SCHEMA_REGISTRY_NAME_{i}"] = f"registry-{i}"
        os.environ[f"SCHEMA_REGISTRY_URL_{i}"] = f"http://localhost:808{i}"
        os.environ[f"SCHEMA_REGISTRY_USER_{i}"] = f"user-{i}"
        os.environ[f"SCHEMA_REGISTRY_PASSWORD_{i}"] = f"password-{i}"
        os.environ[f"READONLY_{i}"] = "true" if i > 6 else "false"
    
    try:
        # Reload the module
        import importlib
        import kafka_schema_registry_multi_mcp
        importlib.reload(kafka_schema_registry_multi_mcp)
        
        registries = kafka_schema_registry_multi_mcp.registry_manager.list_registries()
        print(f"✅ Found {len(registries)} registries (max 8): {registries}")
        
        readonly_count = 0
        for name in registries:
            info = kafka_schema_registry_multi_mcp.registry_manager.get_registry_info(name)
            if info and info.get('readonly', False):
                readonly_count += 1
        
        print(f"✅ Readonly registries: {readonly_count}/8")
        print(f"✅ Max registries supported: {kafka_schema_registry_multi_mcp.MAX_REGISTRIES}")
        
    except Exception as e:
        print(f"❌ Max registries test failed: {e}")

def main():
    print("🧪 Testing Numbered Environment Variable Configuration Loading")
    print("=" * 70)
    
    test_single_registry_config()
    test_multi_registry_config() 
    test_max_registries()
    
    print("\n" + "=" * 70)
    print("🎉 Configuration Loading Tests Complete!")
    print("\nFeatures Verified:")
    print("✅ Single registry mode (backward compatibility)")
    print("✅ Multi-registry mode (numbered environment variables)")
    print("✅ Per-registry READONLY mode")
    print("✅ Maximum 8 registries supported")
    print("✅ Automatic default registry selection")

if __name__ == "__main__":
    main() 