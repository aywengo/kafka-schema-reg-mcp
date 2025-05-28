#!/usr/bin/env python3
"""
Quick test for basic server structure validation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Quick validation test."""
    print("🚀 Quick Basic Server Validation")
    
    try:
        # Test environment setup
        os.environ['SCHEMA_REGISTRY_URL'] = 'http://localhost:38081'
        
        # Test single registry server import and structure
        import kafka_schema_registry_mcp
        print("✅ Single registry MCP server imported")
        
        # Check FastMCP instance
        if hasattr(kafka_schema_registry_mcp, 'mcp'):
            print("✅ FastMCP instance found")
            
            # Check tools
            if hasattr(kafka_schema_registry_mcp.mcp, '_tools'):
                tools_count = len(kafka_schema_registry_mcp.mcp._tools)
                print(f"✅ {tools_count} tools available")
            else:
                print("⚠️ Tools attribute not found")
        else:
            print("❌ FastMCP instance not found")
            return False
        
        # Check registry manager
        if hasattr(kafka_schema_registry_mcp, 'registry_manager'):
            print("✅ Registry manager found")
        else:
            print("❌ Registry manager not found")
            return False
        
        print("✅ Basic server structure validation PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Validation FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 