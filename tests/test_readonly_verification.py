#!/usr/bin/env python3
"""
Simple verification of read-only enforcement in multi-registry MCP server
"""

import os
import sys
import json

def main():
    print("🔍 Verifying read-only enforcement fix...")
    
    # Set up environment for multi-registry mode
    os.environ["SCHEMA_REGISTRY_NAME_1"] = "development"
    os.environ["SCHEMA_REGISTRY_URL_1"] = "http://localhost:38081"
    os.environ["READONLY_1"] = "false"
    
    os.environ["SCHEMA_REGISTRY_NAME_2"] = "production"
    os.environ["SCHEMA_REGISTRY_URL_2"] = "http://localhost:38082" 
    os.environ["READONLY_2"] = "true"
    
    # Clear global READONLY
    os.environ.pop("READONLY", None)
    
    # Add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    try:
        # Import the multi-registry server
        import kafka_schema_registry_multi_mcp as server
        
        print("✅ Multi-registry server imported")
        
        # Test 1: Check registry configuration
        registries = server.list_registries()
        print(f"Configured registries: {[r.get('name', 'unknown') for r in registries if isinstance(r, dict)]}")
        
        # Test 2: Test read-only check function directly
        dev_check = server.check_readonly_mode("development")
        prod_check = server.check_readonly_mode("production")
        
        print(f"DEV readonly check: {dev_check}")
        print(f"PROD readonly check: {prod_check}")
        
        # Test 3: Verify read-only enforcement
        if dev_check is None:
            print("✅ DEV registry: Not in read-only mode")
        else:
            print("❌ DEV registry: Incorrectly in read-only mode")
            
        if prod_check and prod_check.get("readonly_mode"):
            print("✅ PROD registry: Correctly in read-only mode") 
            print("✅ Read-only enforcement fix: WORKING")
            return True
        else:
            print("❌ PROD registry: Not in read-only mode")
            print("❌ Read-only enforcement fix: NOT WORKING")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    print(f"\n🎯 Result: {'SUCCESS' if success else 'FAILURE'}")
    sys.exit(0 if success else 1) 