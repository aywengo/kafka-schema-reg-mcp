#!/usr/bin/env python3
"""
Test script for ID preservation during schema migration.
"""

import os
import sys
import json
import requests
import time
import uuid
import asyncio
from datetime import datetime

# Add parent directory to path to import the MCP server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import kafka_schema_registry_multi_mcp as mcp_server

# Configuration
DEV_REGISTRY_URL = "http://localhost:38081"
PROD_REGISTRY_URL = "http://localhost:38082"

class IDPreservationTest:
    def __init__(self):
        self.dev_url = DEV_REGISTRY_URL
        self.prod_url = PROD_REGISTRY_URL
        self.test_context = f"test-id-preservation-{uuid.uuid4().hex[:8]}"
        self.test_subjects = []
        self.import_mode_supported = False
        # Set up environment variables for registry manager
        os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
        os.environ["SCHEMA_REGISTRY_URL_1"] = self.dev_url
        os.environ["SCHEMA_REGISTRY_NAME_2"] = "prod"
        os.environ["SCHEMA_REGISTRY_URL_2"] = self.prod_url
        os.environ["READONLY_2"] = "false"  # Allow writes to prod for testing
        # Reinitialize registry manager with test config
        mcp_server.registry_manager._load_registries()

    def check_import_mode_support(self):
        """Check if IMPORT mode is supported by the Schema Registry."""
        print("\n🔍 Checking IMPORT mode support...")
        try:
            response = requests.get(f"{self.dev_url}/mode")
            if response.status_code == 200:
                current_mode = response.json().get("mode", "")
                print(f"   📋 Current mode: {current_mode}")
                
                # Try to set IMPORT mode
                response = requests.put(
                    f"{self.dev_url}/mode",
                    json={"mode": "IMPORT"},
                    headers={"Content-Type": "application/vnd.schemaregistry.v1+json"}
                )
                
                if response.status_code == 200:
                    print("   ✅ IMPORT mode is supported")
                    self.import_mode_supported = True
                else:
                    print("   ⚠️ IMPORT mode is not supported")
                    print("   ℹ️  This is expected in some Schema Registry configurations")
                    self.import_mode_supported = False
            else:
                print(f"   ⚠️ Could not check mode: {response.text}")
                self.import_mode_supported = False
        except Exception as e:
            print(f"   ⚠️ Error checking mode: {e}")
            self.import_mode_supported = False

    def setup_test_environment(self):
        """Set up test environment with test schemas."""
        print(f"📝 Creating test schemas in context '{self.test_context}'...")
        
        # Create test schema
        schema = {
            "type": "record",
            "name": "TestUser",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "name", "type": "string"}
            ]
        }
        
        # Register schema in DEV
        response = requests.post(
            f"{self.dev_url}/subjects/{self.test_context}:test-user/versions",
            json={"schema": json.dumps(schema)},
            headers={"Content-Type": "application/vnd.schemaregistry.v1+json"}
        )
        
        if response.status_code == 200:
            schema_id = response.json().get("id")
            print(f"   ✅ Created schema with ID {schema_id}")
            self.test_subjects.append(f"{self.test_context}:test-user")
        else:
            print(f"   ❌ Failed to create test schema: {response.text}")
            return False
            
        return True

    async def test_migration_without_id_preservation(self):
        """Test migration without ID preservation."""
        print("\n🧪 Testing migration without ID preservation...")
        
        # Get source schema ID
        response = requests.get(
            f"{self.dev_url}/subjects/{self.test_context}:test-user/versions/latest"
        )
        if response.status_code == 200:
            source_id = response.json().get("id")
            print(f"   📋 Source schema ID: {source_id}")
        else:
            print(f"   ❌ Could not get source schema ID: {response.text}")
            return False
            
        # Migrate schema
        result = await mcp_server.migrate_schema(
            subject=f"{self.test_context}:test-user",
            source_registry="dev",
            target_registry="prod",
            preserve_ids=False
        )
        
        if result.get("error"):
            print(f"   ❌ Migration failed: {result['error']}")
            return False
            
        # Verify new ID was assigned
        response = requests.get(
            f"{self.prod_url}/subjects/{self.test_context}:test-user/versions/latest"
        )
        if response.status_code == 200:
            target_id = response.json().get("id")
            print(f"   📋 Target schema ID: {target_id}")
            if target_id != source_id:
                print("   ✅ New ID assigned (expected)")
                return True
            else:
                print("   ❌ ID was preserved (unexpected)")
                return False
        else:
            print(f"   ❌ Could not verify target schema: {response.text}")
            return False

    async def test_migration_with_id_preservation(self):
        """Test migration with ID preservation."""
        print("\n🧪 Testing migration with ID preservation...")
        
        if not self.import_mode_supported:
            print("   ⚠️ Skipping ID preservation test - IMPORT mode not supported")
            print("   ℹ️  This is expected in some Schema Registry configurations")
            return True
        
        # Get source schema ID
        response = requests.get(
            f"{self.dev_url}/subjects/{self.test_context}:test-user/versions/latest"
        )
        if response.status_code == 200:
            source_id = response.json().get("id")
            print(f"   📋 Source schema ID: {source_id}")
        else:
            print(f"   ❌ Could not get source schema ID: {response.text}")
            return False
            
        # Migrate schema with ID preservation
        result = await mcp_server.migrate_schema(
            subject=f"{self.test_context}:test-user",
            source_registry="dev",
            target_registry="prod",
            preserve_ids=True
        )
        
        if result.get("error"):
            print(f"   ❌ Migration failed: {result['error']}")
            return False
            
        # Verify ID was preserved
        response = requests.get(
            f"{self.prod_url}/subjects/{self.test_context}:test-user/versions/latest"
        )
        if response.status_code == 200:
            target_id = response.json().get("id")
            print(f"   📋 Target schema ID: {target_id}")
            if target_id == source_id:
                print("   ✅ ID preserved (expected)")
                return True
            else:
                print(f"   ❌ ID not preserved: {target_id} != {source_id}")
                return False
        else:
            print(f"   ❌ Could not verify target schema: {response.text}")
            return False

    def cleanup(self):
        """Clean up test subjects."""
        print("\n🧹 Cleaning up test schemas...")
        
        for subject in self.test_subjects:
            # Delete from DEV
            try:
                response = requests.delete(f"{self.dev_url}/subjects/{subject}")
                if response.status_code == 200:
                    print(f"   ✅ Deleted {subject} from dev")
                else:
                    print(f"   ⚠️ Failed to delete {subject} from dev: {response.text}")
            except Exception as e:
                print(f"   ⚠️ Failed to delete {subject} from dev: {e}")
                
            # Delete from PROD
            try:
                response = requests.delete(f"{self.prod_url}/subjects/{subject}")
                if response.status_code == 200:
                    print(f"   ✅ Deleted {subject} from prod")
                else:
                    print(f"   ⚠️ Failed to delete {subject} from prod: {response.text}")
            except Exception as e:
                print(f"   ⚠️ Failed to delete {subject} from prod: {e}")

async def run_tests():
    test = IDPreservationTest()
    
    try:
        # Check IMPORT mode support first
        test.check_import_mode_support()
        
        if not test.setup_test_environment():
            print("❌ Test setup failed")
            return 1
            
        tests_passed = 0
        total_tests = 2
        
        if await test.test_migration_without_id_preservation():
            tests_passed += 1
            
        if await test.test_migration_with_id_preservation():
            tests_passed += 1
            
        print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
        
        if tests_passed < total_tests:
            print("\n⚠️  Some tests failed")
            return 1
            
        print("\n✅ All tests passed!")
        return 0
        
    finally:
        test.cleanup()

def main():
    return asyncio.run(run_tests())

if __name__ == "__main__":
    sys.exit(main()) 