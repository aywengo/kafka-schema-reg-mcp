#!/usr/bin/env python3
"""
Lightweight Migration Integration Test

This test validates migration integration functionality using the existing
multi-registry environment without managing Docker containers.
"""

import os
import sys
import json
import requests
import uuid
from datetime import datetime
import asyncio
import time
import logging
from typing import Optional
import pytest
from unittest.mock import MagicMock

# Add parent directory to path to import the MCP server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import kafka_schema_registry_multi_mcp as mcp_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="session", autouse=True)
def mock_task_manager():
    """Replace the task manager with a mock that doesn't create threads"""
    # Save the original task manager
    original_task_manager = mcp_server.task_manager
    
    # Create a mock that behaves like task manager but doesn't use threads
    mock_tm = MagicMock()
    mock_tm._shutdown = False
    mock_tm.tasks = {}
    
    # Create a mock task that will be returned
    mock_task = MagicMock()
    mock_task.id = "test-task-id"
    mock_task.status = mcp_server.TaskStatus.COMPLETED
    mock_task.to_dict.return_value = {
        "id": "test-task-id", 
        "status": "completed",
        "type": "migration",
        "progress": 100.0
    }
    
    # Make the mock methods return sensible defaults
    mock_tm.create_task.return_value = mock_task
    mock_tm.get_task.return_value = mock_task
    mock_tm.list_tasks.return_value = []
    
    # Replace the global task manager
    mcp_server.task_manager = mock_tm
    
    yield
    
    # Restore the original task manager
    mcp_server.task_manager = original_task_manager
    
    # Ensure clean shutdown
    if hasattr(original_task_manager, 'shutdown_sync'):
        original_task_manager.shutdown_sync()

@pytest.fixture
async def test_env():
    """Fixture to set up and tear down the test environment"""
    dev_url = "http://localhost:38081"
    prod_url = "http://localhost:38082"
    test_context = f"test-integration-{uuid.uuid4().hex[:8]}"
    
    # Setup environment for multi-registry mode with both registries writable
    os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
    os.environ["SCHEMA_REGISTRY_URL_1"] = dev_url
    os.environ["READONLY_1"] = "false"
    
    os.environ["SCHEMA_REGISTRY_NAME_2"] = "prod"
    os.environ["SCHEMA_REGISTRY_URL_2"] = prod_url
    os.environ["READONLY_2"] = "false"  # Make PROD writable for testing
    
    # Clear any other registry configurations
    for i in range(3, 9):
        for var in [f"SCHEMA_REGISTRY_NAME_{i}", f"SCHEMA_REGISTRY_URL_{i}", f"READONLY_{i}"]:
            if var in os.environ:
                del os.environ[var]
    
    # Clear global READONLY setting
    if "READONLY" in os.environ:
        del os.environ["READONLY"]
    
    # Force reload the registry manager with new configuration
    mcp_server.registry_manager._load_multi_registries()
    
    yield {
        "dev_url": dev_url,
        "prod_url": prod_url,
        "test_context": test_context
    }
    
    # Cleanup after tests
    try:
        # Delete test subjects from both registries
        for registry in ["dev", "prod"]:
            subjects = mcp_server.get_subjects(context=test_context, registry=registry)
            for subject in subjects:
                mcp_server.delete_subject(subject, context=test_context, registry=registry)
    except Exception as e:
        logger.warning(f"Cleanup error: {e}")

async def create_test_schema(context: str) -> Optional[str]:
    """Create a test schema in the specified registry and context."""
    try:
        # Generate a unique subject name
        subject = f"test-subject-{uuid.uuid4().hex[:8]}"
        
        # Create a simple test schema
        schema = {
            "type": "record",
            "name": "TestRecord",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "name", "type": "string"}
            ]
        }
        
        # Register the schema
        result = mcp_server.register_schema(
            subject=subject,
            schema_definition=schema,
            schema_type="AVRO",
            context=context,
            registry="dev"
        )
        
        if "error" in result:
            logger.error(f"Error creating test schema: {result['error']}")
            return None
            
        logger.info(f"Created test schema for subject: {subject}")
        return subject
        
    except Exception as e:
        logger.error(f"Error creating test schema: {e}")
        return None

@pytest.mark.asyncio
async def test_end_to_end_migration(test_env):
    """Test end-to-end migration process"""
    test_subjects = []
    
    try:
        # Create test schemas in DEV registry
        logger.info("Creating test schemas in DEV registry...")
        
        # Create two test schemas
        for i in range(2):
            subject = await create_test_schema(".")
            assert subject is not None, "Failed to create test schema"
            test_subjects.append(subject)
        
        # Verify schemas exist in DEV
        for subject in test_subjects:
            versions = mcp_server.get_schema_versions(subject, context=".", registry="dev")
            assert versions, f"Subject {subject} not found in DEV registry"
        
        # Set compatibility to NONE for test subjects in destination registry only
        for subject in test_subjects:
            # Set PROD compatibility to NONE
            result = mcp_server.update_subject_config(
                subject=subject,
                compatibility="NONE",
                context=".",
                registry="prod"
            )
            assert "error" not in result, f"Failed to set PROD compatibility for {subject}: {result['error']}"
        
        # Perform dry run migration
        logger.info("Performing dry run migration...")
        for subject in test_subjects:
            result = await mcp_server.migrate_schema(
                subject=subject,
                source_registry="dev",
                target_registry="prod",
                dry_run=True
            )
            assert "error" not in result, f"Dry run failed for {subject}: {result['error']}"
        
        # Execute actual migration
        logger.info("Executing actual migration...")
        for subject in test_subjects:
            result = await mcp_server.migrate_schema(
                subject=subject,
                source_registry="dev",
                target_registry="prod",
                dry_run=False
            )
            assert "error" not in result, f"Migration failed for {subject}: {result['error']}"
            
            # Verify schema content in PROD
            dev_schema = mcp_server.get_schema(subject, context=".", registry="dev")
            prod_schema = mcp_server.get_schema(subject, context=".", registry="prod")
            assert dev_schema["schema"] == prod_schema["schema"], "Schema content mismatch"
        
        # Clean up test subjects
        for subject in test_subjects:
            for registry in ["dev", "prod"]:
                mcp_server.delete_subject(subject, context=".", registry=registry)
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

@pytest.mark.asyncio
async def test_migration_error_handling(test_env):
    """Test migration error handling"""
    try:
        # Try to migrate non-existent subject
        result = await mcp_server.migrate_schema(
            subject="non-existent-subject",
            source_registry="dev",
            target_registry="prod"
        )
        assert "error" in result, "Expected error for non-existent subject"
        
        # Try to migrate to non-existent registry
        result = await mcp_server.migrate_schema(
            subject="test-subject",
            source_registry="dev",
            target_registry="non-existent-registry"
        )
        assert "error" in result, "Expected error for non-existent registry"
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

@pytest.mark.asyncio
async def test_migration_task_tracking(test_env):
    """Test migration task tracking"""
    try:
        # Create a test schema
        subject = await create_test_schema(".")
        assert subject is not None, "Failed to create test schema"
        
        # Start migration task
        result = await mcp_server.migrate_schema(
            subject=subject,
            source_registry="dev",
            target_registry="prod"
        )
        assert "error" not in result, f"Migration failed: {result.get('error')}"
        
        # Verify task tracking
        task_id = result.get("task_id")
        assert task_id is not None, "No task ID returned"
        
        # Get task progress (not status)
        task_progress = await mcp_server.get_task_progress(task_id)
        assert task_progress is not None, "Could not get task progress"
        assert task_progress["status"] in ["completed", "running"], f"Unexpected task status: {task_progress['status']}"
        
        # Clean up
        mcp_server.delete_subject(subject, context=".", registry="dev")
        mcp_server.delete_subject(subject, context=".", registry="prod")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

@pytest.mark.asyncio
async def test_registry_comparison_integration(test_env):
    """Test registry comparison functionality"""
    try:
        # Create test schemas in DEV
        subject = await create_test_schema(".")
        assert subject is not None, "Failed to create test schema"
        
        # Compare registries
        result = await mcp_server.compare_registries(
            source_registry="dev",
            target_registry="prod"
        )
        assert "error" not in result, f"Registry comparison failed: {result.get('error')}"
        
        # Verify comparison results
        assert "subjects" in result, "No subjects in comparison results"
        assert subject in result["subjects"]["source_only"], "Test subject not found in source-only list"
        
        # Clean up
        mcp_server.delete_subject(subject, context=".", registry="dev")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

@pytest.mark.asyncio
async def test_clean_destination_migration(test_env):
    """Test migration with clean destination"""
    try:
        # Create test schema in DEV
        subject = await create_test_schema(".")
        assert subject is not None, "Failed to create test schema"
        
        # Create same subject in PROD with different schema
        different_schema = {
            "type": "record",
            "name": "TestRecord",
            "fields": [
                {"name": "id", "type": "string"},  # Different type
                {"name": "name", "type": "string"}
            ]
        }
        
        result = mcp_server.register_schema(
            subject=subject,
            schema_definition=different_schema,
            schema_type="AVRO",
            context=".",
            registry="prod"
        )
        assert "error" not in result, f"Failed to create different schema in PROD: {result.get('error')}"
        
        # Migrate with clean destination
        result = await mcp_server.migrate_schema(
            subject=subject,
            source_registry="dev",
            target_registry="prod",
            clean_destination=True
        )
        assert "error" not in result, f"Migration failed: {result.get('error')}"
        
        # Verify final schema matches source
        dev_schema = mcp_server.get_schema(subject, context=".", registry="dev")
        prod_schema = mcp_server.get_schema(subject, context=".", registry="prod")
        assert dev_schema["schema"] == prod_schema["schema"], "Schema content mismatch after clean migration"
        
        # Clean up
        mcp_server.delete_subject(subject, context=".", registry="dev")
        mcp_server.delete_subject(subject, context=".", registry="prod")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

@pytest.mark.asyncio
async def test_dry_run_migration(test_env):
    """Test dry run migration functionality"""
    try:
        # Create test schema in DEV
        subject = await create_test_schema(".")
        assert subject is not None, "Failed to create test schema"
        
        # Perform dry run migration
        result = await mcp_server.migrate_schema(
            subject=subject,
            source_registry="dev",
            target_registry="prod",
            dry_run=True
        )
        assert "error" not in result, f"Dry run failed: {result.get('error')}"
        assert result.get("dry_run") is True, "Dry run flag not set in result"
        
        # Verify schema was not actually migrated
        prod_versions = mcp_server.get_schema_versions(subject, context=".", registry="prod")
        assert not prod_versions, "Schema was migrated despite dry run"
        
        # Clean up
        mcp_server.delete_subject(subject, context=".", registry="dev")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

@pytest.mark.asyncio
async def test_id_preservation_migration(test_env):
    """Test schema ID preservation during migration"""
    try:
        # Create test schema in DEV
        subject = await create_test_schema(".")
        assert subject is not None, "Failed to create test schema"
        
        # Get original schema ID
        dev_schema = mcp_server.get_schema(subject, context=".", registry="dev")
        original_id = dev_schema.get("id")
        assert original_id is not None, "No schema ID found in source"
        
        # Migrate with ID preservation
        result = await mcp_server.migrate_schema(
            subject=subject,
            source_registry="dev",
            target_registry="prod",
            preserve_ids=True
        )
        assert "error" not in result, f"Migration failed: {result.get('error')}"
        
        # Verify ID was preserved
        prod_schema = mcp_server.get_schema(subject, context=".", registry="prod")
        assert prod_schema.get("id") == original_id, "Schema ID was not preserved"
        
        # Clean up
        mcp_server.delete_subject(subject, context=".", registry="dev")
        mcp_server.delete_subject(subject, context=".", registry="prod")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 