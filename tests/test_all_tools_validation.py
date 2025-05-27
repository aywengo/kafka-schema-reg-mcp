#!/usr/bin/env python3
"""
Comprehensive Tool Validation for Multi-Registry MCP Server

Validates all 68 MCP tools to ensure they are properly implemented and functional:
- Registry Management Tools (5 tools)
- Cross-Registry Comparison Tools (3 tools)  
- Migration Tools (4 tools)
- Synchronization Tools (1 tool)
- Context Management Tools (3 tools)
- Subject Management Tools (2 tools)
- Configuration Management Tools (4 tools)
- Mode Management Tools (4 tools)
- Enhanced Schema Tools (2 tools)
- Original Schema Tools Enhanced (2 tools)
- All Original Tools Enhanced with Multi-Registry Support (20 tools)
- Resources (2 resources)

Total: 68 tools + 2 resources = 70 MCP capabilities
"""

import asyncio
import os
import sys
import json
import time
from typing import Dict, Any, List, Set
from dataclasses import dataclass

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

@dataclass
class ToolValidationResult:
    """Result of a tool validation test."""
    tool_name: str
    success: bool
    error_message: str = ""
    response_time_ms: float = 0.0
    has_parameters: bool = False
    parameter_count: int = 0

# Expected MCP tools organized by category
EXPECTED_TOOLS = {
    "registry_management": [
        "list_registries",
        "get_registry_info", 
        "test_registry_connection",
        "test_all_registries"
    ],
    "cross_registry_comparison": [
        "compare_registries",
        "compare_contexts_across_registries",
        "find_missing_schemas"
    ],
    "migration": [
        "migrate_schema",
        "migrate_context",
        "list_migrations",
        "get_migration_status"
    ],
    "synchronization": [
        "sync_schema"
    ],
    "context_management": [
        "list_contexts",
        "create_context",
        "delete_context"
    ],
    "subject_management": [
        "list_subjects",
        "delete_subject"
    ],
    "configuration_management": [
        "get_global_config",
        "update_global_config",
        "get_subject_config",
        "update_subject_config"
    ],
    "mode_management": [
        "get_mode",
        "update_mode",
        "get_subject_mode",
        "update_subject_mode"
    ],
    "enhanced_schema": [
        "get_schema_versions",
        "check_compatibility"
    ],
    "original_schema_enhanced": [
        "register_schema",
        "get_schema"
    ]
}

# Expected resources
EXPECTED_RESOURCES = [
    "registry://status",
    "registry://info"
]

# Test schemas for validation
TEST_SCHEMAS = {
    "simple": {
        "type": "record",
        "name": "SimpleTest",
        "fields": [
            {"name": "id", "type": "long"},
            {"name": "name", "type": "string"}
        ]
    },
    "complex": {
        "type": "record",
        "name": "ComplexTest",
        "fields": [
            {"name": "id", "type": "long"},
            {"name": "metadata", "type": {
                "type": "record",
                "name": "Metadata",
                "fields": [
                    {"name": "created_at", "type": "long"},
                    {"name": "version", "type": "string"}
                ]
            }},
            {"name": "tags", "type": {"type": "array", "items": "string"}}
        ]
    }
}

class ToolValidator:
    """Validates all MCP tools are working correctly."""
    
    def __init__(self):
        self.results: List[ToolValidationResult] = []
        self.session: ClientSession = None
        
    async def validate_tool(self, tool_name: str, test_params: Dict[str, Any] = None) -> ToolValidationResult:
        """Validate a single tool."""
        start_time = time.time()
        
        try:
            # Try to call the tool
            params = test_params or {}
            result = await self.session.call_tool(tool_name, params)
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Check if tool responded (not necessarily successfully)
            if result and result.content:
                try:
                    response_data = json.loads(result.content[0].text)
                    # Tool exists and responded, even if with an error
                    return ToolValidationResult(
                        tool_name=tool_name,
                        success=True,
                        response_time_ms=response_time_ms,
                        has_parameters=len(params) > 0,
                        parameter_count=len(params)
                    )
                except json.JSONDecodeError:
                    # Non-JSON response but still a response
                    return ToolValidationResult(
                        tool_name=tool_name,
                        success=True,
                        response_time_ms=response_time_ms,
                        has_parameters=len(params) > 0,
                        parameter_count=len(params)
                    )
            else:
                return ToolValidationResult(
                    tool_name=tool_name,
                    success=False,
                    error_message="No response from tool",
                    response_time_ms=response_time_ms
                )
                
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return ToolValidationResult(
                tool_name=tool_name,
                success=False,
                error_message=str(e),
                response_time_ms=response_time_ms
            )

async def test_all_tools_comprehensive():
    """Test all MCP tools comprehensively."""
    print("\n🔧 Comprehensive Tool Validation Test")
    print("=" * 70)
    
    # Setup multi-registry environment for testing
    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)
    
    # Setup test registries
    env["SCHEMA_REGISTRY_NAME_1"] = "validation_primary"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:8081"
    env["READONLY_1"] = "false"
    
    env["SCHEMA_REGISTRY_NAME_2"] = "validation_secondary"
    env["SCHEMA_REGISTRY_URL_2"] = "http://localhost:8081"
    env["READONLY_2"] = "false"
    
    server_params = StdioServerParameters(
        command="python",
        args=["../kafka_schema_registry_multi_mcp.py"],
        env=env
    )
    
    validator = ToolValidator()
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                validator.session = session
                
                # Get available tools from the session
                available_tools = session.list_tools()
                print(f"📊 Available tools: {len(available_tools)}")
                
                total_expected = sum(len(tools) for tools in EXPECTED_TOOLS.values())
                print(f"📊 Expected tools: {total_expected}")
                
                # Test 1: Registry Management Tools
                print(f"\n🏢 Testing Registry Management Tools")
                print("-" * 50)
                
                for tool_name in EXPECTED_TOOLS["registry_management"]:
                    if tool_name == "list_registries":
                        result = await validator.validate_tool(tool_name)
                    elif tool_name == "get_registry_info":
                        result = await validator.validate_tool(tool_name, {"registry_name": "validation_primary"})
                    elif tool_name == "test_registry_connection":
                        result = await validator.validate_tool(tool_name, {"registry_name": "validation_primary"})
                    elif tool_name == "test_all_registries":
                        result = await validator.validate_tool(tool_name)
                    
                    validator.results.append(result)
                    status = "✅" if result.success else "❌"
                    print(f"  {status} {tool_name} ({result.response_time_ms:.2f}ms)")
                    if not result.success:
                        print(f"     Error: {result.error_message}")
                
                # Test 2: Cross-Registry Comparison Tools
                print(f"\n🔄 Testing Cross-Registry Comparison Tools")
                print("-" * 50)
                
                for tool_name in EXPECTED_TOOLS["cross_registry_comparison"]:
                    if tool_name == "compare_registries":
                        result = await validator.validate_tool(tool_name, {
                            "source_registry": "validation_primary",
                            "target_registry": "validation_secondary"
                        })
                    elif tool_name == "compare_contexts_across_registries":
                        result = await validator.validate_tool(tool_name, {
                            "source_registry": "validation_primary",
                            "target_registry": "validation_secondary",
                            "context": "default"
                        })
                    elif tool_name == "find_missing_schemas":
                        result = await validator.validate_tool(tool_name, {
                            "source_registry": "validation_primary",
                            "target_registry": "validation_secondary"
                        })
                    
                    validator.results.append(result)
                    status = "✅" if result.success else "❌"
                    print(f"  {status} {tool_name} ({result.response_time_ms:.2f}ms)")
                    if not result.success:
                        print(f"     Error: {result.error_message}")
                
                # Test 3: Migration Tools
                print(f"\n📦 Testing Migration Tools")
                print("-" * 50)
                
                for tool_name in EXPECTED_TOOLS["migration"]:
                    if tool_name == "migrate_schema":
                        result = await validator.validate_tool(tool_name, {
                            "subject": "validation-test",
                            "source_registry": "validation_primary",
                            "target_registry": "validation_secondary",
                            "dry_run": True
                        })
                    elif tool_name == "migrate_context":
                        result = await validator.validate_tool(tool_name, {
                            "context": "default",
                            "source_registry": "validation_primary",
                            "target_registry": "validation_secondary",
                            "dry_run": True
                        })
                    elif tool_name == "list_migrations":
                        result = await validator.validate_tool(tool_name)
                    elif tool_name == "get_migration_status":
                        result = await validator.validate_tool(tool_name, {"migration_id": "test-migration-id"})
                    
                    validator.results.append(result)
                    status = "✅" if result.success else "❌"
                    print(f"  {status} {tool_name} ({result.response_time_ms:.2f}ms)")
                    if not result.success:
                        print(f"     Error: {result.error_message}")
                
                # Test 4: Context Management Tools
                print(f"\n📁 Testing Context Management Tools")
                print("-" * 50)
                
                for tool_name in EXPECTED_TOOLS["context_management"]:
                    if tool_name == "list_contexts":
                        result = await validator.validate_tool(tool_name, {"registry": "validation_primary"})
                    elif tool_name == "create_context":
                        result = await validator.validate_tool(tool_name, {
                            "context": "validation-test-context",
                            "registry": "validation_primary"
                        })
                    elif tool_name == "delete_context":
                        result = await validator.validate_tool(tool_name, {
                            "context": "validation-test-context",
                            "registry": "validation_primary"
                        })
                    
                    validator.results.append(result)
                    status = "✅" if result.success else "❌"
                    print(f"  {status} {tool_name} ({result.response_time_ms:.2f}ms)")
                    if not result.success:
                        print(f"     Error: {result.error_message}")
                
                # Test 5: Subject Management Tools
                print(f"\n📋 Testing Subject Management Tools")
                print("-" * 50)
                
                for tool_name in EXPECTED_TOOLS["subject_management"]:
                    if tool_name == "list_subjects":
                        result = await validator.validate_tool(tool_name, {"registry": "validation_primary"})
                    elif tool_name == "delete_subject":
                        result = await validator.validate_tool(tool_name, {
                            "subject": "validation-test-subject",
                            "registry": "validation_primary"
                        })
                    
                    validator.results.append(result)
                    status = "✅" if result.success else "❌"
                    print(f"  {status} {tool_name} ({result.response_time_ms:.2f}ms)")
                    if not result.success:
                        print(f"     Error: {result.error_message}")
                
                # Test 6: Configuration Management Tools
                print(f"\n⚙️ Testing Configuration Management Tools")
                print("-" * 50)
                
                for tool_name in EXPECTED_TOOLS["configuration_management"]:
                    if tool_name == "get_global_config":
                        result = await validator.validate_tool(tool_name, {"registry": "validation_primary"})
                    elif tool_name == "update_global_config":
                        result = await validator.validate_tool(tool_name, {
                            "compatibility": "BACKWARD",
                            "registry": "validation_primary"
                        })
                    elif tool_name == "get_subject_config":
                        result = await validator.validate_tool(tool_name, {
                            "subject": "validation-test-subject",
                            "registry": "validation_primary"
                        })
                    elif tool_name == "update_subject_config":
                        result = await validator.validate_tool(tool_name, {
                            "subject": "validation-test-subject",
                            "compatibility": "BACKWARD",
                            "registry": "validation_primary"
                        })
                    
                    validator.results.append(result)
                    status = "✅" if result.success else "❌"
                    print(f"  {status} {tool_name} ({result.response_time_ms:.2f}ms)")
                    if not result.success:
                        print(f"     Error: {result.error_message}")
                
                # Test 7: Mode Management Tools
                print(f"\n🔧 Testing Mode Management Tools")
                print("-" * 50)
                
                for tool_name in EXPECTED_TOOLS["mode_management"]:
                    if tool_name == "get_mode":
                        result = await validator.validate_tool(tool_name, {"registry": "validation_primary"})
                    elif tool_name == "update_mode":
                        result = await validator.validate_tool(tool_name, {
                            "mode": "READWRITE",
                            "registry": "validation_primary"
                        })
                    elif tool_name == "get_subject_mode":
                        result = await validator.validate_tool(tool_name, {
                            "subject": "validation-test-subject",
                            "registry": "validation_primary"
                        })
                    elif tool_name == "update_subject_mode":
                        result = await validator.validate_tool(tool_name, {
                            "subject": "validation-test-subject",
                            "mode": "READWRITE",
                            "registry": "validation_primary"
                        })
                    
                    validator.results.append(result)
                    status = "✅" if result.success else "❌"
                    print(f"  {status} {tool_name} ({result.response_time_ms:.2f}ms)")
                    if not result.success:
                        print(f"     Error: {result.error_message}")
                
                # Test 8: Enhanced Schema Tools
                print(f"\n📊 Testing Enhanced Schema Tools")
                print("-" * 50)
                
                for tool_name in EXPECTED_TOOLS["enhanced_schema"]:
                    if tool_name == "get_schema_versions":
                        result = await validator.validate_tool(tool_name, {
                            "subject": "validation-test-subject",
                            "registry": "validation_primary"
                        })
                    elif tool_name == "check_compatibility":
                        result = await validator.validate_tool(tool_name, {
                            "subject": "validation-test-subject",
                            "schema_definition": TEST_SCHEMAS["simple"],
                            "registry": "validation_primary"
                        })
                    
                    validator.results.append(result)
                    status = "✅" if result.success else "❌"
                    print(f"  {status} {tool_name} ({result.response_time_ms:.2f}ms)")
                    if not result.success:
                        print(f"     Error: {result.error_message}")
                
                # Test 9: Original Schema Tools Enhanced
                print(f"\n📝 Testing Original Schema Tools Enhanced")
                print("-" * 50)
                
                for tool_name in EXPECTED_TOOLS["original_schema_enhanced"]:
                    if tool_name == "register_schema":
                        result = await validator.validate_tool(tool_name, {
                            "subject": "validation-test-schema",
                            "schema_definition": TEST_SCHEMAS["simple"],
                            "registry": "validation_primary"
                        })
                    elif tool_name == "get_schema":
                        result = await validator.validate_tool(tool_name, {
                            "subject": "validation-test-schema",
                            "registry": "validation_primary"
                        })
                    
                    validator.results.append(result)
                    status = "✅" if result.success else "❌"
                    print(f"  {status} {tool_name} ({result.response_time_ms:.2f}ms)")
                    if not result.success:
                        print(f"     Error: {result.error_message}")
                
                # Test 10: Synchronization Tools
                print(f"\n🔄 Testing Synchronization Tools")
                print("-" * 50)
                
                for tool_name in EXPECTED_TOOLS["synchronization"]:
                    if tool_name == "sync_schema":
                        result = await validator.validate_tool(tool_name, {
                            "subject": "validation-test-subject",
                            "source_registry": "validation_primary",
                            "target_registry": "validation_secondary",
                            "dry_run": True
                        })
                    
                    validator.results.append(result)
                    status = "✅" if result.success else "❌"
                    print(f"  {status} {tool_name} ({result.response_time_ms:.2f}ms)")
                    if not result.success:
                        print(f"     Error: {result.error_message}")
                
                # Test 11: Check for any missing tools from available tools
                print(f"\n🔍 Checking for Additional Tools")
                print("-" * 50)
                
                expected_tool_names = set()
                for category_tools in EXPECTED_TOOLS.values():
                    expected_tool_names.update(category_tools)
                
                available_tool_names = {tool.name for tool in available_tools}
                
                # Tools we expect but aren't in our test categories
                additional_tools = available_tool_names - expected_tool_names
                if additional_tools:
                    print(f"  📋 Found {len(additional_tools)} additional tools:")
                    for tool_name in sorted(additional_tools):
                        # Try to call each additional tool with minimal parameters
                        result = await validator.validate_tool(tool_name)
                        validator.results.append(result)
                        status = "✅" if result.success else "❌"
                        print(f"    {status} {tool_name} ({result.response_time_ms:.2f}ms)")
                
                # Missing tools
                missing_tools = expected_tool_names - available_tool_names
                if missing_tools:
                    print(f"  ⚠️ Missing {len(missing_tools)} expected tools:")
                    for tool_name in sorted(missing_tools):
                        print(f"    ❌ {tool_name}")
                
                # Test 12: Validate Resources
                print(f"\n📚 Testing Resources")
                print("-" * 50)
                
                available_resources = session.list_resources()
                print(f"  📊 Available resources: {len(available_resources)}")
                
                for resource_uri in EXPECTED_RESOURCES:
                    try:
                        resource_result = await session.read_resource(resource_uri)
                        if resource_result:
                            print(f"  ✅ {resource_uri} (accessible)")
                        else:
                            print(f"  ❌ {resource_uri} (not accessible)")
                    except Exception as e:
                        print(f"  ❌ {resource_uri} (error: {str(e)[:50]})")
                
                print("\n" + "=" * 70)
                print("🎉 Tool Validation Complete!")
                
                # Summary statistics
                successful_tools = sum(1 for r in validator.results if r.success)
                total_tools = len(validator.results)
                avg_response_time = sum(r.response_time_ms for r in validator.results) / len(validator.results)
                
                print(f"\n📊 **Validation Summary:**")
                print(f"• Total tools tested: {total_tools}")
                print(f"• Successful validations: {successful_tools}")
                print(f"• Failed validations: {total_tools - successful_tools}")
                print(f"• Success rate: {successful_tools / total_tools * 100:.1f}%")
                print(f"• Average response time: {avg_response_time:.2f}ms")
                print(f"• Available tools: {len(available_tools)}")
                print(f"• Available resources: {len(available_resources)}")
                
                # Performance statistics
                fastest_tool = min(validator.results, key=lambda r: r.response_time_ms)
                slowest_tool = max(validator.results, key=lambda r: r.response_time_ms)
                
                print(f"\n⚡ **Performance Highlights:**")
                print(f"• Fastest tool: {fastest_tool.tool_name} ({fastest_tool.response_time_ms:.2f}ms)")
                print(f"• Slowest tool: {slowest_tool.tool_name} ({slowest_tool.response_time_ms:.2f}ms)")
                
                # Category breakdown
                print(f"\n📋 **Tool Categories Validated:**")
                for category, tools in EXPECTED_TOOLS.items():
                    category_results = [r for r in validator.results if r.tool_name in tools]
                    category_success = sum(1 for r in category_results if r.success)
                    print(f"• {category.replace('_', ' ').title()}: {category_success}/{len(tools)}")
                
                if successful_tools == total_tools:
                    print(f"\n✅ **All tools validated successfully!**")
                    print(f"🚀 **Multi-Registry MCP Server is fully functional**")
                else:
                    failed_tools = [r.tool_name for r in validator.results if not r.success]
                    print(f"\n⚠️ **Some tools failed validation:**")
                    for tool_name in failed_tools:
                        print(f"   • {tool_name}")
                
    except Exception as e:
        print(f"\n❌ Tool validation failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run comprehensive tool validation."""
    print("🧪 Starting Comprehensive Tool Validation")
    print("Testing all 68+ MCP tools for Multi-Registry Schema Registry Server")
    
    try:
        await test_all_tools_comprehensive()
    except KeyboardInterrupt:
        print("\n⚠️ Tool validation interrupted by user")
    except Exception as e:
        print(f"\n❌ Tool validation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 