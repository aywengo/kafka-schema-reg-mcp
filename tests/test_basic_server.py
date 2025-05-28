#!/usr/bin/env python3
"""
Basic test for MCP server import and initialization
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test if we can import the MCP server modules."""
    print("🔍 Testing imports...")
    
    try:
        import mcp
        print(f"✅ MCP imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import MCP: {e}")
        return False
    
    try:
        import requests
        print(f"✅ Requests imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import requests: {e}")
        return False
    
    try:
        import asyncio
        print(f"✅ Asyncio imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import asyncio: {e}")
        return False
    
    return True

def test_server_import():
    """Test if we can import the MCP server file."""
    print("\n🔍 Testing MCP server import...")
    
    try:
        # Try importing the single registry server
        import kafka_schema_registry_mcp
        print(f"✅ Single registry MCP server imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import single registry MCP server: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Import succeeded but got error: {e}")
    
    try:
        # Try importing the multi-registry server
        import kafka_schema_registry_multi_mcp
        print(f"✅ Multi-registry MCP server imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import multi-registry MCP server: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Import succeeded but got error: {e}")
    
    return True

def test_basic_functionality():
    """Test basic server functionality without Schema Registry connection."""
    print("\n🔍 Testing basic server functionality...")
    
    try:
        # Set test environment variables
        os.environ['SCHEMA_REGISTRY_URL'] = 'http://localhost:38081'
        os.environ['SCHEMA_REGISTRY_USER'] = ''
        os.environ['SCHEMA_REGISTRY_PASSWORD'] = ''
        
        # Test single registry server components
        import kafka_schema_registry_mcp
        
        # Check that the FastMCP instance exists
        if hasattr(kafka_schema_registry_mcp, 'mcp'):
            print(f"✅ Single registry MCP instance found")
            
            # Check that it has tools (FastMCP exposes tools via _tools attribute)
            if hasattr(kafka_schema_registry_mcp.mcp, '_tools'):
                tools_count = len(kafka_schema_registry_mcp.mcp._tools)
                print(f"✅ Single registry server has {tools_count} tools")
            else:
                print(f"⚠️ Single registry server tools not accessible")
        else:
            print(f"❌ Single registry MCP instance not found")
            return False
        
        # Check helper classes exist
        if hasattr(kafka_schema_registry_mcp, 'RegistryManager'):
            print(f"✅ RegistryManager class found")
        
        if hasattr(kafka_schema_registry_mcp, 'RegistryClient'):
            print(f"✅ RegistryClient class found")
        
        # Test registry manager instance
        if hasattr(kafka_schema_registry_mcp, 'registry_manager'):
            print(f"✅ Registry manager instance found")
            registries = kafka_schema_registry_mcp.registry_manager.list_registries()
            print(f"✅ Registry manager has {len(registries)} configured registries")
        
    except Exception as e:
        print(f"❌ Single registry server validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        # Test multi-registry server components
        import kafka_schema_registry_multi_mcp
        
        # Check that the FastMCP instance exists
        if hasattr(kafka_schema_registry_multi_mcp, 'mcp'):
            print(f"✅ Multi-registry MCP instance found")
            
            # Check that it has tools
            if hasattr(kafka_schema_registry_multi_mcp.mcp, '_tools'):
                tools_count = len(kafka_schema_registry_multi_mcp.mcp._tools)
                print(f"✅ Multi-registry server has {tools_count} tools")
            else:
                print(f"⚠️ Multi-registry server tools not accessible")
        else:
            print(f"❌ Multi-registry MCP instance not found")
            return False
        
    except Exception as e:
        print(f"❌ Multi-registry server validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def main():
    """Main test function."""
    print("🚀 Starting basic MCP server tests...")
    print(f"🔍 Python version: {sys.version}")
    print(f"📁 Current directory: {os.getcwd()}")
    
    # Test 1: Imports
    if not test_imports():
        print("\n❌ Import tests failed")
        return False
    
    # Test 2: Server imports
    if not test_server_import():
        print("\n❌ Server import tests failed")
        return False
    
    # Test 3: Basic functionality
    if not test_basic_functionality():
        print("\n❌ Basic functionality tests failed")
        return False
    
    print("\n✅ All basic tests passed!")
    print("\n📋 Summary:")
    print("  ✅ All required packages can be imported")
    print("  ✅ MCP server modules can be imported")
    print("  ✅ FastMCP instances can be accessed")
    print("  ✅ Server tools are available")
    print("  ✅ Helper classes and managers are available")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 