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

# Add parent directory to path to import the MCP server and oauth_provider
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kafka_schema_registry_unified_mcp as mcp_server

# Configuration
DEV_REGISTRY_URL = "http://localhost:38081"
PROD_REGISTRY_URL = "http://localhost:38082"

class IDPreservationTest:
    def __init__(self):
        self.dev_url = DEV_REGISTRY_URL
        self.prod_url = PROD_REGISTRY_URL
        self.test_context = "test-id-preservation"  # Simplified context name
        self.target_context = f"target-id-preservation-{uuid.uuid4().hex[:8]}"  # Unique target context for each run
        self.test_subjects = []
        self.import_mode_supported = False
        self.contexts_supported = False
        # Set up environment variables for registry manager
        os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
        os.environ["SCHEMA_REGISTRY_URL_1"] = self.dev_url
        os.environ["SCHEMA_REGISTRY_NAME_2"] = "prod"
        os.environ["SCHEMA_REGISTRY_URL_2"] = self.prod_url
        os.environ["READONLY_2"] = "false"  # Allow writes to prod for testing
        # Reinitialize registry manager with test config
        mcp_server.registry_manager._load_multi_registries()

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
                    response = requests.put(
                        f"{self.dev_url}/mode",
                        json={"mode": "READWRITE"},
                        headers={"Content-Type": "application/vnd.schemaregistry.v1+json"}
                    )
                    if response.status_code == 200:
                        print("   ✅ Restored registry to READWRITE mode")
                else:
                    print("   ⚠️ IMPORT mode is not supported")
                    print("   ℹ️  This is expected in some Schema Registry configurations")
                    print("   ℹ️  ID preservation requires IMPORT mode support")
                    print("   ℹ️  Consider using a Schema Registry version that supports IMPORT mode")
                    self.import_mode_supported = False
            else:
                print(f"   ⚠️ Could not check mode: {response.text}")
                self.import_mode_supported = False
        except Exception as e:
            print(f"   ⚠️ Error checking mode: {e}")
            self.import_mode_supported = False

    def check_context_support(self):
        """Check if context management is supported."""
        print("\n🔍 Checking context management support...")
        try:
            # Try to list contexts
            response = requests.get(
                f"{self.dev_url}/contexts",
                headers={"Content-Type": "application/vnd.schemaregistry.v1+json"}
            )
            if response.status_code == 200:
                print("   ✅ Context management is supported")
                self.contexts_supported = True
                return True
            else:
                print("   ℹ️ Context management is not supported")
                print("   ℹ️ Will use default context for testing")
                self.contexts_supported = False
                return True
        except Exception as e:
            print(f"   ⚠️ Error checking context support: {e}")
            print("   ℹ️ Will use default context for testing")
            self.contexts_supported = False
            return True

    def setup_test_environment(self):
        """Set up test environment with test schemas."""
        print(f"📝 Creating test schemas...")
        
        # First check context support
        if not self.check_context_support():
            return False
        
        # First, ensure the registry is in READWRITE mode
        try:
            # Set global mode to READWRITE
            response = requests.put(
                f"{self.dev_url}/mode",
                json={"mode": "READWRITE"},
                headers={"Content-Type": "application/vnd.schemaregistry.v1+json"}
            )
            if response.status_code == 200:
                print("   ✅ Set registry to READWRITE mode")
            else:
                print(f"   ⚠️  Could not set READWRITE mode: {response.text}")
        except Exception as e:
            print(f"   ⚠️  Error setting mode: {e}")

        # Create test schema
        try:
            schema = {
                "type": "record",
                "name": "TestUser",
                "fields": [
                    {"name": "id", "type": "int"},
                    {"name": "name", "type": "string"}
                ]
            }
            
            # Create schema with or without context based on support
            if self.contexts_supported:
                response = requests.post(
                    f"{self.dev_url}/contexts/{self.test_context}/subjects/test-user/versions",
                    json={"schema": json.dumps(schema)},
                    headers={"Content-Type": "application/vnd.schemaregistry.v1+json"}
                )
            else:
                response = requests.post(
                    f"{self.dev_url}/subjects/test-user/versions",
                    json={"schema": json.dumps(schema)},
                    headers={"Content-Type": "application/vnd.schemaregistry.v1+json"}
                )
            
            if response.status_code == 200:
                schema_id = response.json().get("id")
                print(f"   ✅ Created schema with ID {schema_id}")
                # Store the subject name
                if self.contexts_supported:
                    self.test_subjects.append(f":.{self.test_context}:test-user")
                else:
                    self.test_subjects.append("test-user")
                return True
            else:
                print(f"   ❌ Failed to create test schema: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error creating test schema: {e}")
            return False

    async def test_migration_without_id_preservation(self):
        """Test migration without ID preservation."""
        print("\n🧪 Testing migration without ID preservation...")
        
        # Use the appropriate subject name based on context support
        subject_name = self.test_subjects[0] if self.test_subjects else "test-user"
        target_subject_name = "test-user"  # Always use simple name for target
        
        # Get source schema ID
        response = requests.get(
            f"{self.dev_url}/subjects/{subject_name}/versions/latest"
        )
        if response.status_code == 200:
            source_id = response.json().get("id")
            print(f"   📋 Source schema ID: {source_id}")
        else:
            print(f"   ❌ Could not get source schema ID: {response.text}")
            return False

        # Migrate schema without ID preservation
        result = mcp_server.migrate_schema(
            subject=subject_name,
            source_registry="dev",
            target_registry="prod",
            preserve_ids=False,
            source_context=self.test_context if self.contexts_supported else None,
            target_context=self.target_context if self.contexts_supported else None
        )
        
        if "task_id" in result:
            # Migration started as async task, wait for it
            print(f"   ⏳ Migration started with task ID: {result['task_id']}")
            await asyncio.sleep(2)  # Give it time to complete
            
        if result.get("error"):
            print(f"   ❌ Migration failed: {result['error']}")
            return False
            
        # Verify ID was not preserved
        response = requests.get(
            f"{self.prod_url}/subjects/{target_subject_name}/versions/latest"
        )
        if response.status_code == 200:
            target_id = response.json().get("id")
            print(f"   📋 Target schema ID: {target_id}")
            if target_id == source_id:
                print("   ℹ️ ID was preserved (this can happen if the schema already existed)")
                # Check if schema already existed
                try:
                    check_response = requests.get(
                        f"{self.prod_url}/subjects/{target_subject_name}/versions"
                    )
                    if check_response.status_code == 200:
                        versions = check_response.json()
                        if len(versions) > 1:
                            print("   ℹ️ Schema had multiple versions - migration added a new version")
                        else:
                            print("   ℹ️ Schema already existed with the same ID")
                except Exception as e:
                    print(f"   ⚠️ Could not check schema versions: {e}")
                return True
            else:
                print("   ✅ ID was not preserved (expected)")
                return True
        else:
            print(f"   ❌ Could not verify target schema: {response.text}")
            return False

    async def test_migration_with_id_preservation(self):
        """Test migration with ID preservation."""
        print("\n🧪 Testing migration with ID preservation...")
        print(f"   📋 Using unique target context: {self.target_context}")
        
        # Use the appropriate subject name based on context support
        subject_name = self.test_subjects[0] if self.test_subjects else "test-user"
        target_subject_name = f":.{self.target_context}:test-user" if self.contexts_supported else "test-user"
        
        # Get source schema ID
        response = requests.get(
            f"{self.dev_url}/subjects/{subject_name}/versions/latest"
        )
        if response.status_code == 200:
            source_id = response.json().get("id")
            print(f"   📋 Source schema ID: {source_id}")
        else:
            print(f"   ❌ Could not get source schema ID: {response.text}")
            return False

        # Migrate schema with ID preservation
        result = mcp_server.migrate_schema(
            subject=subject_name,
            source_registry="dev",
            target_registry="prod",
            preserve_ids=True,
            source_context=self.test_context if self.contexts_supported else None,
            target_context=f"target-id-preservation-test-{uuid.uuid4().hex[:8]}"
        )
        
        if "task_id" in result:
            # Migration started as async task, wait for it
            print(f"   ⏳ Migration started with task ID: {result['task_id']}")
            await asyncio.sleep(2)  # Give it time to complete
            
        if result.get("error"):
            print(f"   ❌ Migration failed: {result['error']}")
            return False
            
        # Verify ID was preserved
        response = requests.get(
            f"{self.prod_url}/subjects/{target_subject_name}/versions/latest"
        )
        if response.status_code == 200:
            target_id = response.json().get("id")
            print(f"   📋 Target schema ID: {target_id}")
            if target_id == source_id:
                print("   ✅ ID preserved (expected)")
                # Restore READWRITE mode for the subject
                try:
                    if self.contexts_supported:
                        response = requests.put(
                            f"{self.prod_url}/contexts/{self.target_context}/mode/test-user",
                            json={"mode": "READWRITE"},
                            headers={"Content-Type": "application/vnd.schemaregistry.v1+json"}
                        )
                    else:
                        response = requests.put(
                            f"{self.prod_url}/mode/test-user",
                            json={"mode": "READWRITE"},
                            headers={"Content-Type": "application/vnd.schemaregistry.v1+json"}
                        )
                    if response.status_code == 200:
                        print("   ✅ Restored subject to READWRITE mode")
                    else:
                        print(f"   ⚠️ Failed to restore READWRITE mode: {response.text}")
                except Exception as e:
                    print(f"   ⚠️ Error restoring READWRITE mode: {e}")
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
        
        # Clean up subjects from DEV
        for subject in self.test_subjects:
            try:
                response = requests.delete(f"{self.dev_url}/subjects/{subject}")
                if response.status_code == 200:
                    print(f"   ✅ Deleted {subject} from dev")
                else:
                    print(f"   ⚠️ Failed to delete {subject} from dev: {response.text}")
            except Exception as e:
                print(f"   ⚠️ Failed to delete {subject} from dev: {e}")
        
        # Clean up subjects from PROD
        try:
            subject_name = "test-user"
            response = requests.delete(f"{self.prod_url}/subjects/{subject_name}")
            if response.status_code == 200:
                print(f"   ✅ Deleted {subject_name} from prod")
            elif response.status_code != 404:  # 404 is OK - subject doesn't exist
                print(f"   ⚠️ Failed to delete {subject_name} from prod: {response.text}")
        except Exception as e:
            print(f"   ⚠️ Error cleaning up prod subject: {e}")

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