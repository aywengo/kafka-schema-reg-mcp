#!/usr/bin/env python3
"""
Lightweight Migration Tests

This test validates migration functionality using the existing
multi-registry environment without requiring additional setup.
"""

import os
import sys
import json
import requests
import uuid
from datetime import datetime
import pytest
import asyncio
import aiohttp
import atexit
from concurrent.futures import ThreadPoolExecutor

# Add parent directory to path to import the MCP server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import kafka_schema_registry_multi_mcp as mcp_server

# Global executor for cleanup
_executor = None

def cleanup_executor():
    """Cleanup function to be called at exit"""
    global _executor
    if _executor:
        _executor.shutdown(wait=False)
        _executor = None
    # Also cleanup task manager
    if mcp_server.task_manager:
        mcp_server.task_manager._shutdown = True
        if mcp_server.task_manager._executor:
            mcp_server.task_manager._executor.shutdown(wait=False)
            mcp_server.task_manager._executor = None

# Register cleanup
atexit.register(cleanup_executor)

@pytest.fixture(scope="function")
async def test_env():
    """Fixture to set up test environment"""
    global _executor
    
    dev_url = "http://localhost:38081"
    prod_url = "http://localhost:38082"
    
    # Setup environment for multi-registry mode
    os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
    os.environ["SCHEMA_REGISTRY_URL_1"] = dev_url
    os.environ["READONLY_1"] = "false"
    
    os.environ["SCHEMA_REGISTRY_NAME_2"] = "prod"
    os.environ["SCHEMA_REGISTRY_URL_2"] = prod_url
    os.environ["READONLY_2"] = "false"  # Allow writes for testing
    
    # Clear any other registry configurations
    for i in range(3, 9):
        for var in [f"SCHEMA_REGISTRY_NAME_{i}", f"SCHEMA_REGISTRY_URL_{i}", f"READONLY_{i}"]:
            if var in os.environ:
                del os.environ[var]
    
    # Reinitialize registry manager with multi-registry config
    mcp_server.registry_manager._load_registries()
    
    # Create a session for async HTTP requests
    session = aiohttp.ClientSession()
    
    # Create thread pool executor if not exists
    if not _executor:
        _executor = ThreadPoolExecutor(max_workers=10)
        mcp_server.task_manager._executor = _executor
    
    yield {
        "dev_url": dev_url,
        "prod_url": prod_url,
        "session": session
    }
    
    # Cleanup
    await session.close()
    
    # Reset registry manager
    mcp_server.registry_manager.registries.clear()
    mcp_server.registry_manager.default_registry = None
    
    # Cancel any running tasks and cleanup task manager
    try:
        await mcp_server.task_manager.cancel_all_tasks()
    except Exception:
        pass  # Ignore errors during cleanup
    mcp_server.task_manager.reset_queue()
    mcp_server.task_manager._shutdown = True
    if mcp_server.task_manager._executor:
        mcp_server.task_manager._executor.shutdown(wait=False)
        mcp_server.task_manager._executor = None

@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """Cleanup fixture that runs after each test"""
    yield
    # Cancel any remaining tasks and cleanup task manager
    try:
        await mcp_server.task_manager.cancel_all_tasks()
    except Exception:
        pass  # Ignore errors during cleanup
    mcp_server.task_manager.reset_queue()
    mcp_server.task_manager._shutdown = True
    if mcp_server.task_manager._executor:
        mcp_server.task_manager._executor.shutdown(wait=False)
        mcp_server.task_manager._executor = None

async def wait_for_task_completion(task_id: str, timeout: int = 30) -> bool:
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

@pytest.mark.asyncio
async def test_default_context_url_building(test_env):
    """Test that default context URL building works correctly"""
    print(f"\n🔗 Testing default context URL building...")
    
    try:
        # Get client
        client = mcp_server.registry_manager.get_registry("dev")
        if not client:
            print(f"   ❌ Could not get DEV registry client")
            return False
        
        # Test URL building with different context values
        url_none = client.build_context_url("/subjects", None)
        url_dot = client.build_context_url("/subjects", ".")
        url_empty = client.build_context_url("/subjects", "")
        url_production = client.build_context_url("/subjects", "production")
        
        print(f"   📊 URL Building Results:")
        print(f"      context=None: {url_none}")
        print(f"      context='.': {url_dot}")
        print(f"      context='': {url_empty}")
        print(f"      context='production': {url_production}")
        
        # Verify the fix: context='.' should be treated like None
        if url_none != url_dot:
            print(f"   ❌ FAILURE: context=None and context='.' produce different URLs")
            return False
        
        # Verify that production context is different
        if url_none == url_production:
            print(f"   ❌ FAILURE: default context URL same as production context URL")
            return False
        
        print(f"   ✅ Default context URL building is correct")
        return True
        
    except Exception as e:
        print(f"   ❌ Default context URL building test failed: {e}")
        return False

@pytest.mark.asyncio
async def test_registry_comparison(test_env):
    """Test registry comparison functionality"""
    print(f"\n📊 Testing registry comparison...")
    
    try:
        # Compare dev and prod registries
        comparison = await mcp_server.compare_registries("dev", "prod")
        
        if "error" in comparison:
            print(f"   ❌ Registry comparison failed: {comparison['error']}")
            return False
        
        # Wait for task completion if it's an async task
        if "task_id" in comparison:
            task_completed = await wait_for_task_completion(comparison["task_id"])
            if not task_completed:
                print(f"   ❌ Registry comparison task did not complete")
                return False
            
            # Get the final result
            task = mcp_server.task_manager.get_task(comparison["task_id"])
            if not task or not task.result:
                print(f"   ❌ No result from registry comparison task")
                return False
            
            comparison = task.result
        
        print(f"   ✅ Registry comparison successful")
        
        subjects_info = comparison.get('subjects', {})
        if subjects_info:
            source_total = subjects_info.get('source_total', 0)
            target_total = subjects_info.get('target_total', 0)
            common = len(subjects_info.get('common', []))
            source_only = len(subjects_info.get('source_only', []))
            target_only = len(subjects_info.get('target_only', []))
            
            print(f"      📈 Comparison Results:")
            print(f"         DEV subjects: {source_total}")
            print(f"         PROD subjects: {target_total}")
            print(f"         Common: {common}")
            print(f"         DEV only: {source_only}")
            print(f"         PROD only: {target_only}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Registry comparison test failed: {e}")
        return False

@pytest.mark.asyncio
async def test_migration_tools_availability(test_env):
    """Test that migration tools are available and working"""
    print(f"\n🛠️  Testing migration tools availability...")
    
    try:
        # Test find_missing_schemas
        missing_schemas = await mcp_server.find_missing_schemas("dev", "prod")
        
        if "error" in missing_schemas:
            print(f"   ❌ find_missing_schemas failed: {missing_schemas['error']}")
            return False
        
        # Wait for task completion if it's an async task
        if "task_id" in missing_schemas:
            task_completed = await wait_for_task_completion(missing_schemas["task_id"])
            if not task_completed:
                print(f"   ❌ find_missing_schemas task did not complete")
                return False
            
            # Get the final result
            task = mcp_server.task_manager.get_task(missing_schemas["task_id"])
            if not task or not task.result:
                print(f"   ❌ No result from find_missing_schemas task")
                return False
            
            missing_schemas = task.result
        
        print(f"   ✅ find_missing_schemas working")
        print(f"      Missing schemas: {missing_schemas.get('missing_count', 0)}")
        
        # Test compare_contexts_across_registries (if contexts exist)
        try:
            context_comparison = await mcp_server.compare_contexts_across_registries("dev", "prod", ".")
            
            if "error" not in context_comparison:
                # Wait for task completion if it's an async task
                if "task_id" in context_comparison:
                    task_completed = await wait_for_task_completion(context_comparison["task_id"])
                    if not task_completed:
                        print(f"   ❌ compare_contexts_across_registries task did not complete")
                        return False
                    
                    # Get the final result
                    task = mcp_server.task_manager.get_task(context_comparison["task_id"])
                    if not task or not task.result:
                        print(f"   ❌ No result from compare_contexts_across_registries task")
                        return False
                    
                    context_comparison = task.result
                
                print(f"   ✅ compare_contexts_across_registries working")
                subjects_info = context_comparison.get('subjects', {})
                if subjects_info:
                    print(f"      Default context - DEV: {subjects_info.get('source_total', 0)}, PROD: {subjects_info.get('target_total', 0)}")
            else:
                print(f"   ⚠️  compare_contexts_across_registries: {context_comparison['error']}")
        except Exception as e:
            print(f"   ⚠️  compare_contexts_across_registries error: {e}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Migration tools availability test failed: {e}")
        return False

if __name__ == "__main__":
    try:
        pytest.main([__file__, "-v"])
    finally:
        # Ensure cleanup happens even if tests are interrupted
        cleanup_executor() 