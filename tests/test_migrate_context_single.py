#!/usr/bin/env python3
"""
Test migrate_context Docker configuration generation for single-registry mode.
"""

import os
import sys
import json

# Add parent directory to path to import the MCP server
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import kafka_schema_registry_mcp as mcp_server

def test_single_registry_migrate_context():
    """Test that migrate_context generates proper Docker configuration in single-registry mode."""
    print("🧪 Testing migrate_context Docker configuration generation (single-registry mode)")
    
    # Set up single-registry environment
    os.environ["SCHEMA_REGISTRY_URL"] = "http://localhost:8081"
    os.environ["SCHEMA_REGISTRY_USER"] = "admin"
    os.environ["SCHEMA_REGISTRY_PASSWORD"] = "secret"
    
    # Clear existing registries and reinitialize
    mcp_server.registry_manager.registries.clear()
    mcp_server.registry_manager.default_registry = None
    
    # Force re-read of environment variables
    mcp_server.SCHEMA_REGISTRY_URL = os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8081")
    mcp_server.SCHEMA_REGISTRY_USER = os.getenv("SCHEMA_REGISTRY_USER", "")
    mcp_server.SCHEMA_REGISTRY_PASSWORD = os.getenv("SCHEMA_REGISTRY_PASSWORD", "")
    
    # Reinitialize registry manager
    mcp_server.registry_manager._load_registries()
    
    # Call migrate_context
    result = mcp_server.migrate_context(
        context="dev-context",
        source_registry="default",
        target_registry="default",
        target_context="prod-context",
        preserve_ids=True,
        dry_run=True,
        migrate_all_versions=True
    )
    
    # Check for errors
    if "error" in result:
        print(f"❌ Error generating config: {result['error']}")
        return False
    
    print(f"✅ Successfully generated Docker configuration")
    
    # Validate the result structure
    required_keys = ["migration_type", "tool", "documentation", "source", "target", 
                     "options", "files_to_create", "instructions", "warnings"]
    
    for key in required_keys:
        if key not in result:
            print(f"❌ Missing required key: {key}")
            return False
    
    print(f"✅ All required keys present")
    
    # Check source and target
    source = result["source"]
    target = result["target"]
    
    if source["url"] != target["url"]:
        print(f"❌ In single-registry mode, source and target URLs should be the same")
        return False
    
    if source["context"] == target["context"]:
        print(f"❌ Source and target contexts should be different")
        return False
    
    print(f"✅ Single-registry configuration correct")
    print(f"   Source: {source['url']} (context: {source['context']})")
    print(f"   Target: {target['url']} (context: {target['context']})")
    
    # Check warnings for single-registry mode
    warnings = result.get("warnings", [])
    single_registry_warning_found = any("same URL" in warning for warning in warnings)
    
    if not single_registry_warning_found:
        print(f"❌ No single-registry warning found")
        return False
    
    print(f"✅ Single-registry warning correctly generated")
    
    # Check .env file content
    env_content = result["files_to_create"][".env"]["content"]
    
    env_checks = [
        "SCHEMA_REGISTRY_URL=http://localhost:8081",
        "SCHEMA_REGISTRY_USERNAME=admin",
        "SCHEMA_REGISTRY_PASSWORD=secret",
        "TARGET_SCHEMA_REGISTRY_URL=http://localhost:8081",
        "TARGET_SCHEMA_REGISTRY_USERNAME=admin",
        "TARGET_SCHEMA_REGISTRY_PASSWORD=secret",
        "SOURCE_CONTEXT=dev-context",
        "TARGET_CONTEXT=prod-context"
    ]
    
    for check in env_checks:
        if check not in env_content:
            print(f"❌ Missing in .env: {check}")
            return False
    
    print(f"✅ .env file content correct for single-registry mode")
    
    print(f"\n✅ All validations passed!")
    print(f"✅ migrate_context correctly generates Docker configuration for single-registry mode")
    return True

if __name__ == "__main__":
    success = test_single_registry_migrate_context()
    sys.exit(0 if success else 1) 