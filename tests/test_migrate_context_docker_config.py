#!/usr/bin/env python3
"""
Test migrate_context Docker command generation functionality.

This test validates that migrate_context correctly generates Docker 
run commands for the kafka-schema-reg-migrator tool.
"""

import os
import sys
import asyncio
import json

# Add parent directory to path to import the MCP server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import kafka_schema_registry_unified_mcp as mcp_server

async def test_docker_command_generation():
    """Test that migrate_context generates proper Docker command."""
    print("🧪 Testing migrate_context Docker command generation")
    
    # Set up test environment variables
    os.environ["SCHEMA_REGISTRY_NAME_1"] = "source-test"
    os.environ["SCHEMA_REGISTRY_URL_1"] = "http://source-registry:8081"
    os.environ["SCHEMA_REGISTRY_USER_1"] = "source_user"
    os.environ["SCHEMA_REGISTRY_PASSWORD_1"] = "source_pass"
    
    os.environ["SCHEMA_REGISTRY_NAME_2"] = "target-test"
    os.environ["SCHEMA_REGISTRY_URL_2"] = "http://target-registry:8082"
    os.environ["SCHEMA_REGISTRY_USER_2"] = "target_user"
    os.environ["SCHEMA_REGISTRY_PASSWORD_2"] = "target_pass"
    os.environ["READONLY_2"] = "false"
    
    # Reload registry manager to pick up new environment
    mcp_server.registry_manager._load_multi_registries()
    
    # Call migrate_context
    result = await mcp_server.migrate_context(
        source_registry="source-test",
        target_registry="target-test",
        context="test-context",
        target_context="prod-context",
        preserve_ids=True,
        dry_run=True,
        migrate_all_versions=True
    )
    
    # Check for errors
    if "error" in result:
        print(f"❌ Error generating command: {result['error']}")
        return False
    
    print(f"✅ Successfully generated Docker command")
    
    # Validate the result structure
    required_keys = ["message", "reason", "tool", "documentation", "docker_command", 
                     "migration_details", "instructions", "env_variables", "warnings"]
    
    for key in required_keys:
        if key not in result:
            print(f"❌ Missing required key: {key}")
            return False
    
    print(f"✅ All required keys present")
    
    # Check message and reason
    if "external kafka-schema-reg-migrator tool" not in result["message"]:
        print(f"❌ Unexpected message: {result['message']}")
        return False
    
    if "single schema migration" not in result["reason"]:
        print(f"❌ Unexpected reason: {result['reason']}")
        return False
    
    # Check tool name
    if result["tool"] != "kafka-schema-reg-migrator":
        print(f"❌ Unexpected tool: {result['tool']}")
        return False
    
    # Check documentation URLs
    if "github.com/aywengo/kafka-schema-reg-migrator" not in result["documentation"]:
        print(f"❌ Wrong documentation URL: {result['documentation']}")
        return False
    
    print(f"✅ Basic fields correct")
    
    # Check migration details
    details = result["migration_details"]
    source = details["source"]
    target = details["target"]
    options = details["options"]
    
    if source["registry"] != "source-test" or source["url"] != "http://source-registry:8081" or source["context"] != "test-context":
        print(f"❌ Wrong source details: {source}")
        return False
    
    if target["registry"] != "target-test" or target["url"] != "http://target-registry:8082" or target["context"] != "prod-context":
        print(f"❌ Wrong target details: {target}")
        return False
    
    if not options["preserve_ids"] or not options["dry_run"] or not options["migrate_all_versions"]:
        print(f"❌ Wrong options: {options}")
        return False
    
    print(f"✅ Migration details correct")
    
    # Check docker command
    docker_cmd = result["docker_command"]
    
    required_in_command = [
        "docker run -it --rm",
        "aywengo/kafka-schema-reg-migrator:latest",
        "SOURCE_SCHEMA_REGISTRY_URL=http://source-registry:8081",
        "DEST_SCHEMA_REGISTRY_URL=http://target-registry:8082",
        "SOURCE_USERNAME=source_user",
        "SOURCE_PASSWORD=source_pass",
        "DEST_USERNAME=target_user",
        "DEST_PASSWORD=target_pass",
        "ENABLE_MIGRATION=true",
        "DRY_RUN=true",
        "PRESERVE_IDS=true",
        "SOURCE_CONTEXT=test-context",
        "DEST_CONTEXT=prod-context",
        "DEST_IMPORT_MODE=true"
    ]
    
    for check in required_in_command:
        if check not in docker_cmd:
            print(f"❌ Missing in docker command: {check}")
            return False
    
    print(f"✅ Docker command correct")
    
    # Check environment variables
    env_vars = result["env_variables"]
    
    required_env_vars = [
        "SOURCE_SCHEMA_REGISTRY_URL=http://source-registry:8081",
        "DEST_SCHEMA_REGISTRY_URL=http://target-registry:8082",
        "ENABLE_MIGRATION=true",
        "DRY_RUN=true",
        "PRESERVE_IDS=true",
        "SOURCE_USERNAME=source_user",
        "SOURCE_PASSWORD=source_pass",
        "DEST_USERNAME=target_user",
        "DEST_PASSWORD=target_pass",
        "SOURCE_CONTEXT=test-context",
        "DEST_CONTEXT=prod-context",
        "DEST_IMPORT_MODE=true"
    ]
    
    for env_var in required_env_vars:
        if env_var not in env_vars:
            print(f"❌ Missing environment variable: {env_var}")
            return False
    
    print(f"✅ Environment variables correct")
    
    # Check instructions
    if not isinstance(result["instructions"], list):
        print(f"❌ Instructions should be a list")
        return False
    
    if len(result["instructions"]) < 5:
        print(f"❌ Not enough instructions provided")
        return False
    
    # Should contain the docker command in instructions
    instructions_text = " ".join(result["instructions"])
    if docker_cmd not in instructions_text:
        print(f"❌ Docker command not found in instructions")
        return False
    
    print(f"✅ Instructions correct")
    
    # Check warnings
    warnings = result["warnings"]
    if not isinstance(warnings, list):
        print(f"❌ Warnings should be a list")
        return False
    
    # Should have warnings about external tool, Docker requirement, and dry run
    expected_warnings = ["external Docker container", "Docker is installed", "DRY RUN"]
    for expected in expected_warnings:
        if not any(expected in warning for warning in warnings):
            print(f"❌ Missing expected warning about: {expected}")
            return False
    
    print(f"✅ Warnings correct")
    
    print(f"✅ All validations passed!")
    return True

async def test_default_context():
    """Test with default context (.)"""
    print("\n🧪 Testing default context handling")
    
    result = await mcp_server.migrate_context(
        source_registry="source-test",
        target_registry="target-test",
        # No context specified - should default to "."
        preserve_ids=False,  # Test without preserve_ids
        dry_run=False,
        migrate_all_versions=False
    )
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return False
    
    # Check that default context is used
    details = result["migration_details"]
    if details["source"]["context"] != "." or details["target"]["context"] != ".":
        print(f"❌ Default context not set correctly: {details}")
        return False
    
    # Check that context env vars are not included for default context
    env_vars = result["env_variables"]
    context_vars = [var for var in env_vars if "CONTEXT" in var]
    if context_vars:
        print(f"❌ Context variables should not be included for default context: {context_vars}")
        return False
    
    # Check that IMPORT mode is not set when not preserving IDs
    import_mode_vars = [var for var in env_vars if "DEST_IMPORT_MODE" in var]
    if import_mode_vars:
        print(f"❌ IMPORT mode should not be set when not preserving IDs: {import_mode_vars}")
        return False
    
    # Check that non-dry-run warning is present
    warnings = result["warnings"]
    non_dry_run_warning = any("actual data migration" in warning for warning in warnings)
    if not non_dry_run_warning:
        print(f"❌ Missing non-dry-run warning")
        return False
    
    print(f"✅ Default context and options handled correctly")
    return True

async def test_single_registry_mode():
    """Test error handling for single registry mode."""
    print("\n🧪 Testing single registry mode error")
    
    # Temporarily set to single registry mode
    original_mode = mcp_server.REGISTRY_MODE
    mcp_server.REGISTRY_MODE = "single"
    
    try:
        result = await mcp_server.migrate_context(
            source_registry="source-test",
            target_registry="target-test"
        )
        
        if "error" not in result:
            print(f"❌ Expected error for single registry mode")
            return False
        
        if "single-registry mode" not in result["error"]:
            print(f"❌ Wrong error message: {result['error']}")
            return False
        
        if result.get("registry_mode") != "single":
            print(f"❌ Wrong registry_mode in response: {result.get('registry_mode')}")
            return False
        
        print(f"✅ Single registry mode error handled correctly")
        return True
        
    finally:
        # Restore original mode
        mcp_server.REGISTRY_MODE = original_mode

async def test_missing_registry():
    """Test error handling for missing registry."""
    print("\n🧪 Testing missing registry error")
    
    result = await mcp_server.migrate_context(
        source_registry="nonexistent-registry",
        target_registry="target-test"
    )
    
    if "error" not in result:
        print(f"❌ Expected error for missing registry")
        return False
    
    if "not found" not in result["error"]:
        print(f"❌ Wrong error message: {result['error']}")
        return False
    
    print(f"✅ Missing registry error handled correctly")
    return True

async def main():
    """Run all tests."""
    print("🚀 Testing migrate_context Docker Command Generation")
    print("=" * 60)
    
    tests = [
        ("Docker Command Generation", test_docker_command_generation),
        ("Default Context Handling", test_default_context),
        ("Single Registry Mode Error", test_single_registry_mode),
        ("Missing Registry Error", test_missing_registry)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            if await test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ migrate_context correctly generates Docker commands")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 