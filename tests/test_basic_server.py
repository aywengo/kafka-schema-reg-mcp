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
        
        # Try to create server instance (this should work even without connection)
        from kafka_schema_registry_mcp import KafkaSchemaRegistryServer
        server = KafkaSchemaRegistryServer()
        print(f"✅ Single registry server instance created")
        
        # Test tool listing
        tools = server.list_tools()
        print(f"✅ Single registry server has {len(tools)} tools")
        
    except Exception as e:
        print(f"❌ Single registry server creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        # Test multi-registry server
        from kafka_schema_registry_multi_mcp import MultiRegistryKafkaSchemaRegistryServer
        multi_server = MultiRegistryKafkaSchemaRegistryServer()
        print(f"✅ Multi-registry server instance created")
        
        # Test tool listing
        multi_tools = multi_server.list_tools()
        print(f"✅ Multi-registry server has {len(multi_tools)} tools")
        
    except Exception as e:
        print(f"❌ Multi-registry server creation failed: {e}")
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
    print("  ✅ Server instances can be created")
    print("  ✅ Tools can be listed")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 