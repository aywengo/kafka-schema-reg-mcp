#!/usr/bin/env python3
"""
All Versions Migration Test

This test validates that the enhanced migrate_context function can preserve
the complete schema evolution history by migrating all versions of schemas,
not just the latest version.
"""

import os
import sys
import json
import uuid
import requests
import time
import asyncio
from datetime import datetime
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import kafka_schema_registry_multi_mcp as mcp_server

# Configuration
DEV_REGISTRY_URL = "http://localhost:38081"
PROD_REGISTRY_URL = "http://localhost:38082"

class AllVersionsMigrationTest:
    """Test class for all-versions migration scenarios"""
    
    def __init__(self):
        # Initialize URLs
        self.dev_url = DEV_REGISTRY_URL
        self.prod_url = PROD_REGISTRY_URL
        
        # Create unique contexts for this test run
        self.source_context = f"test-source-{uuid.uuid4().hex[:8]}"
        self.target_context = f"test-target-{uuid.uuid4().hex[:8]}"
        self.test_subjects = []
        
        # Set up environment variables for registry manager
        os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
        os.environ["SCHEMA_REGISTRY_URL_1"] = self.dev_url
        os.environ["SCHEMA_REGISTRY_NAME_2"] = "prod"
        os.environ["SCHEMA_REGISTRY_URL_2"] = self.prod_url
        os.environ["READONLY_2"] = "false"  # Allow writes to prod for testing
        
        # Reinitialize registry manager with test config
        mcp_server.registry_manager._load_registries()
        
        # Initialize registry manager
        self.registry_manager = mcp_server.registry_manager
        
    async def setup_test_contexts(self):
        """Create test contexts in both registries."""
        print(f"\n=== Setting Up Test Contexts ===")
        
        # Create source context in dev
        result = mcp_server.create_context(self.source_context, registry="dev")
        if "error" in result:
            raise Exception(f"Failed to create source context: {result['error']}")
        print(f"✓ Created source context: {self.source_context}")
        
        # Create target context in prod
        result = mcp_server.create_context(self.target_context, registry="prod")
        if "error" in result:
            raise Exception(f"Failed to create target context: {result['error']}")
        print(f"✓ Created target context: {self.target_context}")
        
        return True
        
    async def create_schema_evolution(self, subject: str, num_versions: int = 3):
        """Create multiple versions of a schema for testing."""
        import copy
        # Create initial schema
        base_schema = {
            "type": "record",
            "name": "TestRecord",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "name", "type": "string"}
            ]
        }
        
        # Create multiple versions
        for i in range(num_versions):
            schema = copy.deepcopy(base_schema)
            # Add a new field for each version (ensure unique field name, and make it optional for compatibility)
            for j in range(i + 1):
                schema["fields"].append({
                    "name": f"field_{j}",
                    "type": "string",
                    "default": ""
                })
            # Register schema using the top-level function
            result = mcp_server.register_schema(
                subject=subject,
                schema_definition=schema,
                schema_type="AVRO",
                context=self.source_context,
                registry="dev"
            )
            if "error" in result:
                raise Exception(f"Failed to register schema version {i+1}: {result['error']}")
            print(f"✓ Registered schema version {i+1}")
        return True
        
    async def verify_schema_versions(self, subject: str, registry: str, context: str, expected_versions: int):
        """Verify that a schema has the expected number of versions."""
        versions = mcp_server.get_schema_versions(subject, context=context, registry=registry)
        if isinstance(versions, dict) and "error" in versions:
            raise Exception(f"Error getting versions: {versions['error']}")
        if len(versions) != expected_versions:
            raise Exception(f"Expected {expected_versions} versions, got {len(versions)}")
        print(f"✓ Verified {len(versions)} versions in {registry} registry")
        return True
        
    async def test_all_versions_migration(self):
        """Test migration of all versions."""
        print("\n=== Testing All Versions Migration ===")
        
        # Create test schemas
        subject = f"test-all-versions-{uuid.uuid4().hex[:6]}"
        self.test_subjects.append(subject)
        
        # Create schema versions in source context
        await self.create_schema_evolution(subject)
        
        # Verify source has multiple versions
        await self.verify_schema_versions(subject, "dev", self.source_context, 3)
        
        # Migrate all versions - migrate_context is async
        result = await mcp_server.migrate_context(
            source_registry="dev",
            target_registry="prod",
            context=self.source_context,
            target_context=self.target_context,
            preserve_ids=True,
            dry_run=False
        )
        
        if "error" in result:
            raise Exception(f"Migration failed: {result['error']}")
            
        # Verify target has all versions
        await self.verify_schema_versions(subject, "prod", self.target_context, 3)
        
        print("✓ All versions migration successful")
        return True
        
    async def cleanup_test_contexts(self):
        """Clean up test contexts and schemas from both registries."""
        print("\n=== Cleaning Up Test Contexts ===")
        
        # Clean up subjects first
        for registry in ["dev", "prod"]:
            context = self.source_context if registry == "dev" else self.target_context
            for subject in self.test_subjects:
                try:
                    result = await mcp_server.delete_subject(subject, context=context, registry=registry)
                    if isinstance(result, dict) and "error" in result:
                        print(f"Warning: Failed to delete {subject} from {registry}: {result['error']}")
                    else:
                        print(f"Deleted {subject} from {registry}")
                except Exception as e:
                    print(f"Warning: Failed to delete {subject} from {registry}: {str(e)}")
        
        # Clean up contexts
        for registry in ["dev", "prod"]:
            context = self.source_context if registry == "dev" else self.target_context
            try:
                # Delete context using clear_context_batch
                result = mcp_server.clear_context_batch(
                    context=context,
                    registry=registry,
                    delete_context_after=True,
                    dry_run=False
                )
                if "error" in result:
                    print(f"Warning: Failed to delete context {context} from {registry}: {result['error']}")
                else:
                    print(f"Deleted context {context} from {registry}")
            except Exception as e:
                print(f"Warning: Failed to delete context {context} from {registry}: {str(e)}")
        
        return True
        
    async def run_all_tests(self):
        """Run all tests."""
        try:
            # Set up test contexts
            await self.setup_test_contexts()
            
            # Run tests
            await self.test_all_versions_migration()
            
            print("\n=== All Tests Completed Successfully ===")
            return True
            
        except Exception as e:
            print(f"\n❌ Test Failed: {str(e)}")
            return False
            
        finally:
            # Clean up
            await self.cleanup_test_contexts()

async def main():
    test = AllVersionsMigrationTest()
    success = await test.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main()) 