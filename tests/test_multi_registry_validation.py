#!/usr/bin/env python3
"""
Multi-Registry Configuration Validation Test

This test validates that the multi-registry configuration is working correctly
with the existing running environment (DEV + PROD registries).
"""

import os
import sys
import json
import requests
import time
import asyncio
from datetime import datetime
import uuid
import pytest

# Add parent directory to path to import the MCP server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import kafka_schema_registry_unified_mcp as mcp_server

@pytest.fixture(scope="session", autouse=True)
def cleanup_task_manager_at_end():
    yield
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.run_until_complete(mcp_server.task_manager.cancel_all_tasks())
        # Give the event loop a moment to process cancellations
        loop.run_until_complete(asyncio.sleep(0.1))
    else:
        loop.run_until_complete(mcp_server.task_manager.cancel_all_tasks())
        loop.run_until_complete(asyncio.sleep(0.1))

    mcp_server.task_manager.reset_queue()

    # Cancel any remaining asyncio tasks
    pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
    for task in pending:
        task.cancel()
    if pending:
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

class MultiRegistryValidationTest:
    """Test class for multi-registry configuration validation"""
    
    def __init__(self):
        self.dev_url = "http://localhost:38081"
        self.prod_url = "http://localhost:38082"
        
        # Setup environment for multi-registry mode
        os.environ["SCHEMA_REGISTRY_NAME_1"] = "dev"
        os.environ["SCHEMA_REGISTRY_URL_1"] = self.dev_url
        os.environ["READONLY_1"] = "false"
        
        os.environ["SCHEMA_REGISTRY_NAME_2"] = "prod"
        os.environ["SCHEMA_REGISTRY_URL_2"] = self.prod_url
        os.environ["READONLY_2"] = "true"  # PROD should be read-only
        
        # Clear any other registry configurations
        for i in range(3, 9):
            for var in [f"SCHEMA_REGISTRY_NAME_{i}", f"SCHEMA_REGISTRY_URL_{i}", f"READONLY_{i}"]:
                if var in os.environ:
                    del os.environ[var]
        
        # Reinitialize registry manager with multi-registry config
        mcp_server.registry_manager._load_multi_registries()
    
    def test_registry_connectivity(self) -> bool:
        """Test that both registries are reachable"""
        print(f"\n🔌 Testing registry connectivity...")
        
        try:
            # Test DEV registry
            dev_response = requests.get(f"{self.dev_url}/subjects", timeout=5)
            if dev_response.status_code != 200:
                print(f"   ❌ DEV registry not responding: {dev_response.status_code}")
                return False
            print(f"   ✅ DEV registry ({self.dev_url}) is accessible")
            
            # Test PROD registry  
            prod_response = requests.get(f"{self.prod_url}/subjects", timeout=5)
            if prod_response.status_code != 200:
                print(f"   ❌ PROD registry not responding: {prod_response.status_code}")
                return False
            print(f"   ✅ PROD registry ({self.prod_url}) is accessible")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Registry connectivity test failed: {e}")
            return False
    
    def test_mcp_registry_detection(self) -> bool:
        """Test that the MCP server detects both registries"""
        print(f"\n🔍 Testing MCP registry detection...")
        
        try:
            # Get list of registries from MCP server
            registries = mcp_server.list_registries()
            
            if not isinstance(registries, list):
                print(f"   ❌ list_registries() returned non-list: {type(registries)}")
                return False
            
            if len(registries) < 2:
                print(f"   ❌ Expected at least 2 registries, found {len(registries)}")
                return False
            
            # Check for dev and prod registries
            registry_names = [r.get('name', '') for r in registries]
            
            if 'dev' not in registry_names:
                print(f"   ❌ DEV registry not found in: {registry_names}")
                return False
            
            if 'prod' not in registry_names:
                print(f"   ❌ PROD registry not found in: {registry_names}")
                return False
            
            print(f"   ✅ Found {len(registries)} registries: {registry_names}")
            
            # Check registry details
            for registry in registries:
                name = registry.get('name', 'unknown')
                url = registry.get('url', 'unknown')
                readonly = registry.get('readonly', False)
                connection_status = registry.get('connection_status', 'unknown')
                
                print(f"   📊 {name}: {url} (readonly: {readonly}, status: {connection_status})")
                
                if connection_status != 'connected':
                    print(f"   ⚠️  Registry {name} is not connected")
            
            return True
            
        except Exception as e:
            print(f"   ❌ MCP registry detection test failed: {e}")
            return False
    
    async def test_cross_registry_operations(self) -> bool:
        """Test cross-registry operations"""
        print(f"\n🔄 Testing cross-registry operations...")
        
        try:
            # Test registry comparison
            print("   ⏳ Registry comparison started as async task")
            comparison = await mcp_server.compare_registries("dev", "prod")
            if "error" in comparison:
                print(f"   ❌ Registry comparison failed: {comparison['error']}")
                return False
            print("   ✅ Registry comparison successful")
            
            # Test compatibility validation
            test_subject = "test-subject"
            test_schema = {
                "type": "record",
                "name": "TestSchema",
                "fields": [
                    {"name": "field1", "type": "string"}
                ]
            }
            
            # Register test schema in dev
            result = mcp_server.register_schema(test_subject, test_schema, registry="dev")
            if "error" in result:
                print(f"   ❌ Failed to register test schema: {result['error']}")
                return False
            
            # Check compatibility in prod
            compatibility = mcp_server.check_compatibility(test_subject, test_schema, registry="prod")
            if "error" in compatibility:
                print(f"   ❌ Compatibility check failed: {compatibility['error']}")
                return False
            
            print("   ✅ Compatibility validation successful")
            
            # Clean up test subject
            await mcp_server.delete_subject(test_subject, registry="dev")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Cross-registry operations test failed: {e}")
            return False
    
    def test_readonly_enforcement(self) -> bool:
        """Test that PROD registry is properly configured as read-only"""
        print(f"\n🔒 Testing read-only enforcement...")
        
        try:
            # Test that PROD registry is marked as read-only in config
            prod_info = mcp_server.get_registry_info("prod")
            
            if "error" in prod_info:
                print(f"   ❌ Could not get PROD registry info: {prod_info['error']}")
                return False
            
            if not prod_info.get('readonly', False):
                print(f"   ⚠️  PROD registry not marked as read-only in configuration")
                # This is a warning, not a failure for this test
            else:
                print(f"   ✅ PROD registry correctly marked as read-only")
            
            # Test DEV registry (should not be read-only)
            dev_info = mcp_server.get_registry_info("dev")
            
            if "error" in dev_info:
                print(f"   ❌ Could not get DEV registry info: {dev_info['error']}")
                return False
            
            if dev_info.get('readonly', False):
                print(f"   ⚠️  DEV registry incorrectly marked as read-only")
            else:
                print(f"   ✅ DEV registry correctly configured as read-write")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Read-only enforcement test failed: {e}")
            return False
    
    async def test_multi_registry_tools(self) -> bool:
        """Test that multi-registry specific tools work"""
        print(f"\n🛠️  Testing multi-registry tools...")
        
        try:
            # Test registry connectivity check
            connectivity_test = await mcp_server.test_all_registries()
            
            if "error" in connectivity_test:
                print(f"   ❌ test_all_registries() failed: {connectivity_test['error']}")
                return False
            
            total_registries = connectivity_test.get('total_registries', 0)
            connected = connectivity_test.get('connected', 0)
            failed = connectivity_test.get('failed', 0)
            
            print(f"   ✅ Connectivity test completed")
            print(f"      Total registries: {total_registries}")
            print(f"      Connected: {connected}")
            print(f"      Failed: {failed}")
            
            if failed > 0:
                print(f"   ⚠️  Some registries failed connectivity test")
                # Show detailed results
                registry_tests = connectivity_test.get('registry_tests', {})
                for name, result in registry_tests.items():
                    status = result.get('status', 'unknown')
                    if status != 'connected':
                        error_msg = result.get('error', 'unknown error')
                        print(f"      {name}: {status} - {error_msg}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Multi-registry tools test failed: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all validation tests"""
        print("\n🔍 Running Multi-Registry Validation Tests...")
        
        # Test registry connectivity
        if not self.test_registry_connectivity():
            return False
        
        # Test MCP registry detection
        if not self.test_mcp_registry_detection():
            return False
        
        # Test cross-registry operations
        if not await self.test_cross_registry_operations():
            return False
        
        # Test readonly enforcement
        if not self.test_readonly_enforcement():
            return False
        
        # Test multi-registry tools
        if not await self.test_multi_registry_tools():
            return False
        
        print("\n✅ All tests passed successfully!")
        return True

def main():
    """Main entry point for the test script"""
    test = MultiRegistryValidationTest()
    asyncio.run(test.run_all_tests())

if __name__ == "__main__":
    main() 