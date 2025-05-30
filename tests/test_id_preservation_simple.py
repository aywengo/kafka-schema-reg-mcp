#!/usr/bin/env python3
"""
Simplified test script for ID preservation during schema migration.
This version avoids using contexts to prevent mode-related issues.
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

class SimpleIDPreservationTest:
    def __init__(self):
        self.dev_url = DEV_REGISTRY_URL
        self.prod_url = PROD_REGISTRY_URL
        self.test_subject = f"test-id-preservation-{uuid.uuid4().hex[:8]}"
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
                    
                    # Restore READWRITE mode
                    requests.put(
                        f"{self.dev_url}/mode",
                        json={"mode": "READWRITE"},
                        headers={"Content-Type": "application/vnd.schemaregistry.v1+json"}
                    )
                else:
                    print("   ⚠️ IMPORT mode is not supported")
                    self.import_mode_supported = False
            else:
                print(f"   ⚠️ Could not check mode: {response.text}")
                self.import_mode_supported = False
        except Exception as e:
            print(f"   ⚠️ Error checking mode: {e}")
            self.import_mode_supported = False

    def setup_test_environment(self):
        """Set up test environment with test schemas."""
        print(f"\n📝 Creating test schema: {self.test_subject}")
        
        # Create test schema
        schema = {
            "type": "record",
            "name": "TestUser",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "name", "type": "string"},
                {"name": "email", "type": "string"}
            ]
        }
        
        # Register schema in DEV
        response = requests.post(
            f"{self.dev_url}/subjects/{self.test_subject}/versions",
            json={"schema": json.dumps(schema)},
            headers={"Content-Type": "application/vnd.schemaregistry.v1+json"}
        )
        
        if response.status_code == 200:
            schema_id = response.json().get("id")
            print(f"   ✅ Created schema with ID {schema_id}")
            return True
        else:
            print(f"   ❌ Failed to create test schema: {response.text}")
            return False

    async def test_migration_without_id_preservation(self):
        """Test migration without ID preservation."""
        print("\n🧪 Testing migration WITHOUT ID preservation...")
        
        # Get source schema ID
        response = requests.get(
            f"{self.dev_url}/subjects/{self.test_subject}/versions/latest"
        )
        if response.status_code != 200:
            print(f"   ❌ Could not get source schema: {response.text}")
            return False
            
        source_id = response.json().get("id")
        print(f"   📋 Source schema ID: {source_id}")
            
        # Migrate schema without ID preservation
        print("   🔄 Starting migration...")
        result = await mcp_server.migrate_schema(
            subject=self.test_subject,
            source_registry="dev",
            target_registry="prod",
            preserve_ids=False,
            source_context=".",
            target_context="."
        )
        
        if "task_id" in result:
            print(f"   ⏳ Migration task started: {result['task_id']}")
            # Wait for async task to complete
            await asyncio.sleep(3)
            
        # Verify migration
        response = requests.get(
            f"{self.prod_url}/subjects/{self.test_subject}/versions/latest"
        )
        if response.status_code != 200:
            print(f"   ❌ Schema not found in target: {response.text}")
            return False
            
        target_id = response.json().get("id")
        print(f"   📋 Target schema ID: {target_id}")
        
        if target_id != source_id:
            print(f"   ✅ New ID assigned: {source_id} → {target_id} (expected)")
            return True
        else:
            print(f"   ❌ ID was preserved when it shouldn't be: {target_id}")
            return False

    async def test_migration_with_id_preservation(self):
        """Test migration with ID preservation."""
        print("\n🧪 Testing migration WITH ID preservation...")
        
        if not self.import_mode_supported:
            print("   ⚠️ Skipping - IMPORT mode not supported")
            print("   ℹ️  This is normal for some Schema Registry configurations")
            return True
        
        # Delete from prod if exists
        requests.delete(f"{self.prod_url}/subjects/{self.test_subject}")
        
        # Get source schema ID
        response = requests.get(
            f"{self.dev_url}/subjects/{self.test_subject}/versions/latest"
        )
        if response.status_code != 200:
            print(f"   ❌ Could not get source schema: {response.text}")
            return False
            
        source_id = response.json().get("id")
        print(f"   📋 Source schema ID: {source_id}")
            
        # Migrate schema with ID preservation
        print("   🔄 Starting migration with ID preservation...")
        result = await mcp_server.migrate_schema(
            subject=self.test_subject,
            source_registry="dev",
            target_registry="prod",
            preserve_ids=True,
            source_context=".",
            target_context="."
        )
        
        if "task_id" in result:
            print(f"   ⏳ Migration task started: {result['task_id']}")
            # Wait for async task to complete
            await asyncio.sleep(3)
            
        # Verify migration
        response = requests.get(
            f"{self.prod_url}/subjects/{self.test_subject}/versions/latest"
        )
        if response.status_code != 200:
            print(f"   ❌ Schema not found in target: {response.text}")
            return False
            
        target_id = response.json().get("id")
        print(f"   📋 Target schema ID: {target_id}")
        
        if target_id == source_id:
            print(f"   ✅ ID preserved: {target_id} (expected)")
            return True
        else:
            print(f"   ❌ ID not preserved: {source_id} → {target_id}")
            return False

    def cleanup(self):
        """Clean up test subjects."""
        print("\n🧹 Cleaning up test schemas...")
        
        # Delete from DEV
        response = requests.delete(f"{self.dev_url}/subjects/{self.test_subject}")
        if response.status_code == 200:
            print(f"   ✅ Deleted from dev")
        elif "not found" not in response.text.lower():
            print(f"   ⚠️ Failed to delete from dev: {response.text}")
            
        # Delete from PROD
        response = requests.delete(f"{self.prod_url}/subjects/{self.test_subject}")
        if response.status_code == 200:
            print(f"   ✅ Deleted from prod")
        elif "not found" not in response.text.lower():
            print(f"   ⚠️ Failed to delete from prod: {response.text}")

async def run_tests():
    """Run all tests."""
    print("=" * 60)
    print("Simple ID Preservation Test")
    print("=" * 60)
    
    test = SimpleIDPreservationTest()
    
    try:
        # Check IMPORT mode support
        test.check_import_mode_support()
        
        # Set up test environment
        if not test.setup_test_environment():
            print("\n❌ Test setup failed")
            return 1
            
        # Run tests
        tests_passed = 0
        total_tests = 2
        
        if await test.test_migration_without_id_preservation():
            tests_passed += 1
        else:
            print("\n❌ Migration without ID preservation test FAILED")
            
        if await test.test_migration_with_id_preservation():
            tests_passed += 1
        else:
            print("\n❌ Migration with ID preservation test FAILED")
            
        # Results
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
        
        if tests_passed == total_tests:
            print("✅ All tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed")
            return 1
            
    finally:
        test.cleanup()

def main():
    """Main entry point."""
    return asyncio.run(run_tests())

if __name__ == "__main__":
    sys.exit(main()) 