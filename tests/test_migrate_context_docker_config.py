#!/usr/bin/env python3
"""
Test migrate_context Docker configuration generation functionality.

This test validates that migrate_context correctly generates Docker 
configuration files and instructions for the kafka-schema-reg-migrator tool.
"""

import os
import sys
import asyncio
import json

# Add parent directory to path to import the MCP server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import kafka_schema_registry_unified_mcp as mcp_server

async def test_docker_config_generation():
    """Test that migrate_context generates proper Docker configuration."""
    print("🧪 Testing migrate_context Docker configuration generation")
    
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
        print(f"❌ Error generating config: {result['error']}")
        return False
    
    print(f"✅ Successfully generated Docker configuration")
    
    # Validate the result structure
    required_keys = ["migration_type", "tool", "documentation", "source", "target", 
                     "options", "files_to_create", "instructions"]
    
    for key in required_keys:
        if key not in result:
            print(f"❌ Missing required key: {key}")
            return False
    
    print(f"✅ All required keys present")
    
    # Check migration type
    if result["migration_type"] != "Docker-based Context Migration":
        print(f"❌ Unexpected migration_type: {result['migration_type']}")
        return False
    
    # Check tool name
    if result["tool"] != "kafka-schema-reg-migrator":
        print(f"❌ Unexpected tool: {result['tool']}")
        return False
    
    # Check source configuration
    source = result["source"]
    if source["registry"] != "source-test":
        print(f"❌ Wrong source registry: {source['registry']}")
        return False
    if source["url"] != "http://source-registry:8081":
        print(f"❌ Wrong source URL: {source['url']}")
        return False
    if source["context"] != "test-context":
        print(f"❌ Wrong source context: {source['context']}")
        return False
    
    print(f"✅ Source configuration correct")
    
    # Check target configuration
    target = result["target"]
    if target["registry"] != "target-test":
        print(f"❌ Wrong target registry: {target['registry']}")
        return False
    if target["url"] != "http://target-registry:8082":
        print(f"❌ Wrong target URL: {target['url']}")
        return False
    if target["context"] != "prod-context":
        print(f"❌ Wrong target context: {target['context']}")
        return False
    
    print(f"✅ Target configuration correct")
    
    # Check options
    options = result["options"]
    if options["preserve_ids"] != True:
        print(f"❌ preserve_ids should be True")
        return False
    if options["dry_run"] != True:
        print(f"❌ dry_run should be True")
        return False
    if options["migrate_all_versions"] != True:
        print(f"❌ migrate_all_versions should be True")
        return False
    
    print(f"✅ Options correct")
    
    # Check files to create
    files = result["files_to_create"]
    required_files = [".env", "docker-compose.yml", "migrate-context.sh"]
    
    for file in required_files:
        if file not in files:
            print(f"❌ Missing file: {file}")
            return False
        
        if "content" not in files[file]:
            print(f"❌ Missing content for file: {file}")
            return False
    
    print(f"✅ All required files present")
    
    # Check .env file content
    env_content = files[".env"]["content"]
    env_checks = [
        "SCHEMA_REGISTRY_URL=http://source-registry:8081",
        "SCHEMA_REGISTRY_USERNAME=source_user",
        "SCHEMA_REGISTRY_PASSWORD=source_pass",
        "TARGET_SCHEMA_REGISTRY_URL=http://target-registry:8082",
        "TARGET_SCHEMA_REGISTRY_USERNAME=target_user",
        "TARGET_SCHEMA_REGISTRY_PASSWORD=target_pass",
        "SOURCE_CONTEXT=test-context",
        "TARGET_CONTEXT=prod-context",
        "PRESERVE_SCHEMA_IDS=true",
        "MIGRATE_ALL_VERSIONS=true",
        "DRY_RUN=true"
    ]
    
    for check in env_checks:
        if check not in env_content:
            print(f"❌ Missing in .env: {check}")
            return False
    
    print(f"✅ .env file content correct")
    
    # Check docker-compose.yml content
    compose_content = files["docker-compose.yml"]["content"]
    compose_checks = [
        "aywengo/kafka-schema-reg-migrator:latest",
        "MODE=migrate-context",
        "--source-context", "test-context",
        "--target-context", "prod-context"
    ]
    
    for check in compose_checks:
        if check not in compose_content:
            print(f"❌ Missing in docker-compose.yml: {check}")
            return False
    
    print(f"✅ docker-compose.yml content correct")
    
    # Check shell script
    script_content = files["migrate-context.sh"]["content"]
    if files["migrate-context.sh"].get("make_executable") != True:
        print(f"❌ Shell script should be marked as executable")
        return False
    
    script_checks = [
        "docker run -it --rm",
        "aywengo/kafka-schema-reg-migrator:latest",
        "--dry-run",
        "--preserve-ids",
        "--all-versions"
    ]
    
    for check in script_checks:
        if check not in script_content:
            print(f"❌ Missing in shell script: {check}")
            return False
    
    print(f"✅ Shell script content correct")
    
    # Check instructions
    if not isinstance(result["instructions"], list):
        print(f"❌ Instructions should be a list")
        return False
    
    if len(result["instructions"]) < 5:
        print(f"❌ Not enough instructions provided")
        return False
    
    print(f"✅ Instructions provided")
    
    # Check warnings
    if "warnings" not in result:
        print(f"❌ Missing warnings section")
        return False
    
    print(f"✅ All validations passed!")
    return True

async def test_readonly_warning():
    """Test that readonly target registry generates appropriate warning."""
    print("\n🧪 Testing readonly target warning")
    
    # Set target as readonly
    os.environ["READONLY_2"] = "true"
    mcp_server.registry_manager._load_multi_registries()
    
    result = await mcp_server.migrate_context(
        source_registry="source-test",
        target_registry="target-test",
        dry_run=True
    )
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return False
    
    # Check for readonly warning
    warnings = result.get("warnings", [])
    readonly_warning_found = any("READONLY" in warning for warning in warnings)
    
    if not readonly_warning_found:
        print(f"❌ No readonly warning found")
        return False
    
    print(f"✅ Readonly warning correctly generated")
    return True

async def test_non_dry_run_warning():
    """Test that non-dry-run generates appropriate warning."""
    print("\n🧪 Testing non-dry-run warning")
    
    # Reset readonly
    os.environ["READONLY_2"] = "false"
    mcp_server.registry_manager._load_multi_registries()
    
    result = await mcp_server.migrate_context(
        source_registry="source-test",
        target_registry="target-test",
        dry_run=False  # Non-dry-run
    )
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return False
    
    # Check for actual migration warning
    warnings = result.get("warnings", [])
    actual_migration_warning_found = any("actual data migration" in warning for warning in warnings)
    
    if not actual_migration_warning_found:
        print(f"❌ No actual migration warning found")
        return False
    
    print(f"✅ Actual migration warning correctly generated")
    return True

async def main():
    """Run all tests."""
    print("🚀 Testing migrate_context Docker Configuration Generation")
    print("=" * 60)
    
    tests = [
        ("Docker Config Generation", test_docker_config_generation),
        ("Readonly Warning", test_readonly_warning),
        ("Non-Dry-Run Warning", test_non_dry_run_warning)
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
        print("✅ migrate_context correctly generates Docker configuration")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 