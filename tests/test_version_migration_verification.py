#!/usr/bin/env python3
"""
Version Migration Verification Test

This test validates that all versions of schemas are properly migrated
between registries, ensuring complete schema evolution history is preserved.
"""

import os
import sys
import json
import uuid
import asyncio
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory to path to import the MCP server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import kafka_schema_registry_multi_mcp as mcp_server

class VersionMigrationVerificationTest:
    """Test class for verifying complete version migration"""
    
    def __init__(self):
        self.dev_url = "http://localhost:38081"
        self.prod_url = "http://localhost:38082"
        self.test_context = f"test-version-verify-{uuid.uuid4().hex[:8]}"
        self.test_subjects = []
        self.is_multi_registry = False
        
        # Detect if we're in multi-registry mode
        try:
            dev_response = requests.get(f"{self.dev_url}/subjects", timeout=5)
            prod_response = requests.get(f"{self.prod_url}/subjects", timeout=5)
            if dev_response.status_code == 200 and prod_response.status_code == 200:
                self.is_multi_registry = True
                print(f"🔍 Detected multi-registry environment (DEV + PROD)")
        except Exception:
            print(f"🔍 Detected single-registry environment (DEV only)")
            # In single registry mode, use the same registry for both source and target
            self.prod_url = self.dev_url
        
        # Setup test environment variables
        if self.is_multi_registry:
            # Multi-registry setup
            os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
            os.environ["SCHEMA_REGISTRY_URL_1"] = self.dev_url
            os.environ["SCHEMA_REGISTRY_NAME_2"] = "prod" 
            os.environ["SCHEMA_REGISTRY_URL_2"] = self.prod_url
            os.environ["READONLY_2"] = "false"  # Allow writes to prod for testing
        else:
            # Single registry setup
            os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
            os.environ["SCHEMA_REGISTRY_URL_1"] = self.dev_url
            # Clear any multi-registry environment variables
            for i in range(2, 9):
                for var in [f"SCHEMA_REGISTRY_NAME_{i}", f"SCHEMA_REGISTRY_URL_{i}", f"READONLY_{i}"]:
                    if var in os.environ:
                        del os.environ[var]
        
        # Reinitialize registry manager with test config
        mcp_server.registry_manager._load_registries()
    
    def create_schema_evolution(self) -> bool:
        """Create a schema with multiple versions to test evolution"""
        print(f"📝 Creating schema evolution in context '{self.test_context}'...")
        
        # Create a test subject
        subject = f"user-events-evolution-{uuid.uuid4().hex[:6]}"
        self.test_subjects.append(subject)
        
        # Base schema (v1)
        schema_v1 = {
            "type": "record",
            "name": "UserEvent",
            "namespace": "com.example.events",
            "fields": [
                {"name": "userId", "type": "string"},
                {"name": "eventType", "type": "string"},
                {"name": "timestamp", "type": "long"}
            ]
        }
        
        # Add optional field (v2)
        schema_v2 = {
            "type": "record",
            "name": "UserEvent",
            "namespace": "com.example.events",
            "fields": [
                {"name": "userId", "type": "string"},
                {"name": "eventType", "type": "string"},
                {"name": "timestamp", "type": "long"},
                {"name": "metadata", "type": ["null", "string"], "default": None}
            ]
        }
        
        # Add another field (v3)
        schema_v3 = {
            "type": "record",
            "name": "UserEvent",
            "namespace": "com.example.events",
            "fields": [
                {"name": "userId", "type": "string"},
                {"name": "eventType", "type": "string"},
                {"name": "timestamp", "type": "long"},
                {"name": "metadata", "type": ["null", "string"], "default": None},
                {"name": "version", "type": "int", "default": 1}
            ]
        }
        
        schemas = [schema_v1, schema_v2, schema_v3]
        created_count = 0
        
        for i, schema in enumerate(schemas, 1):
            try:
                # Create in dev registry with context
                url = f"{self.dev_url}/contexts/{self.test_context}/subjects/{subject}/versions"
                payload = {"schema": json.dumps(schema)}
                
                response = requests.post(
                    url,
                    headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    schema_id = response.json().get("id")
                    print(f"   ✅ Created version {i} of {subject} with ID {schema_id}")
                    created_count += 1
                else:
                    print(f"   ❌ Failed to create version {i}: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"   ❌ Error creating version {i}: {e}")
        
        print(f"📊 Created {created_count}/{len(schemas)} schema versions")
        return created_count == len(schemas)
    
    def get_schema_versions(self, subject: str, registry: str, context: str) -> List[Dict[str, Any]]:
        """Get all versions of a schema"""
        try:
            versions_result = mcp_server.get_schema_versions(subject, context, registry)
            if isinstance(versions_result, dict) and "error" in versions_result:
                return []
            if not isinstance(versions_result, list):
                return []
            return versions_result
        except Exception:
            return []
    
    async def verify_version_migration(self) -> bool:
        """Verify that all versions were migrated correctly"""
        print(f"\n🧪 Verifying version migration...")
        
        if not self.test_subjects:
            print(f"   ❌ No test subjects available")
            return False
        
        subject = self.test_subjects[0]
        
        try:
            # Get source versions
            source_versions = self.get_schema_versions(subject, "dev", self.test_context)
            print(f"   📋 Source has {len(source_versions)} versions of {subject}")
            
            if not source_versions:
                print(f"   ❌ No source versions found")
                return False
            
            # Clear target if in multi-registry mode
            if self.is_multi_registry:
                try:
                    # Delete any existing schemas in target
                    url = f"{self.prod_url}/contexts/{self.test_context}/subjects/{subject}"
                    requests.delete(url, timeout=5)
                except Exception:
                    pass
            
            # Perform migration
            target_registry = "prod" if self.is_multi_registry else "dev"
            
            # Use migrate_schema to perform actual migration
            print(f"   🚀 Migrating schema '{subject}' from dev to {target_registry}...")
            migration_result = await mcp_server.migrate_schema(
                subject=subject,
                source_registry="dev",
                target_registry=target_registry,
                source_context=self.test_context,
                target_context=self.test_context,
                preserve_ids=True,
                migrate_all_versions=True,  # Important: migrate all versions
                dry_run=False
            )
            
            # Wait for task completion if it's an async task
            if "task_id" in migration_result:
                print(f"   ⏳ Waiting for migration task {migration_result['task_id']} to complete...")
                task_completed = await self._wait_for_task_completion(migration_result["task_id"])
                if not task_completed:
                    print(f"   ❌ Migration task did not complete")
                    return False
                
                # Get the final result
                task = mcp_server.task_manager.get_task(migration_result["task_id"])
                if not task or not task.result:
                    print(f"   ❌ No result from migration task")
                    return False
                
                migration_result = task.result
            
            if "error" in migration_result:
                print(f"   ❌ Migration failed: {migration_result['error']}")
                return False
            
            # Get target versions
            target_versions = self.get_schema_versions(subject, target_registry, self.test_context)
            print(f"   📋 Target has {len(target_versions)} versions of {subject}")
            
            if len(target_versions) != len(source_versions):
                print(f"   ❌ Version count mismatch: source={len(source_versions)}, target={len(target_versions)}")
                return False
            
            # Verify each version
            for i, (source_ver, target_ver) in enumerate(zip(source_versions, target_versions), 1):
                print(f"   🔍 Verifying version {i}...")
                
                # Check version number
                if source_ver.get("version") != target_ver.get("version"):
                    print(f"   ❌ Version number mismatch: source={source_ver.get('version')}, target={target_ver.get('version')}")
                    return False
                
                # Check schema content
                source_schema = source_ver.get("schema", "")
                target_schema = target_ver.get("schema", "")
                
                if source_schema != target_schema:
                    print(f"   ❌ Schema content mismatch in version {i}")
                    return False
                
                print(f"   ✅ Version {i} verified")
            
            print(f"   ✅ All versions migrated successfully")
            return True
            
        except Exception as e:
            print(f"   ❌ Version migration verification failed: {e}")
            return False
    
    async def _wait_for_task_completion(self, task_id: str, timeout: int = 30) -> bool:
        """Wait for a task to complete with timeout"""
        start_time = datetime.now()
        while True:
            task = mcp_server.task_manager.get_task(task_id)
            if not task:
                return False
            
            if task.status in [mcp_server.TaskStatus.COMPLETED, mcp_server.TaskStatus.FAILED, mcp_server.TaskStatus.CANCELLED]:
                return task.status == mcp_server.TaskStatus.COMPLETED
            
            if (datetime.now() - start_time).total_seconds() > timeout:
                return False
            
            await asyncio.sleep(0.1)
    
    def cleanup_test_schemas(self):
        """Clean up test schemas from both registries"""
        print(f"\n🧹 Cleaning up test schemas...")
        
        for subject in self.test_subjects:
            try:
                # Clean up from dev registry
                url = f"{self.dev_url}/contexts/{self.test_context}/subjects/{subject}"
                requests.delete(url, timeout=5)
                
                # Clean up from prod registry if in multi-registry mode
                if self.is_multi_registry:
                    url = f"{self.prod_url}/contexts/{self.test_context}/subjects/{subject}"
                    requests.delete(url, timeout=5)
                    
            except Exception as e:
                print(f"   ⚠️  Error cleaning up {subject}: {e}")
    
    async def run_all_tests(self) -> bool:
        """Run all test scenarios"""
        print(f"🚀 Starting Version Migration Verification Tests")
        print(f"============================================================")
        print(f"This test validates that all schema versions are properly")
        print(f"migrated between registries")
        print(f"============================================================")
        
        try:
            # Create test schemas
            if not self.create_schema_evolution():
                print(f"❌ Failed to create test schemas")
                return False
            
            # Run tests
            test_results = [
                await self.verify_version_migration()
            ]
            
            # Print summary
            passed = sum(1 for result in test_results if result)
            total = len(test_results)
            print(f"\n📊 Test Results: {passed}/{total} tests passed")
            
            if passed < total:
                print(f"\n⚠️  {total - passed} tests failed")
            
            return passed == total
            
        finally:
            # Always clean up
            self.cleanup_test_schemas()

async def main():
    """Main entry point"""
    test = VersionMigrationVerificationTest()
    success = await test.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main()) 